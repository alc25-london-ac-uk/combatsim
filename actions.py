from typing import Optional
import random
from dataclasses import dataclass

from enums import AttackResult, ActionType, RollType, DamageType
from dice import saving_throw, attack_roll, damage_roll, resolve_advantage
from combatant import Combatant, Weapon, MeleeWeapon, RangedWeapon, Spell, Ability
from effects import Concentrating
from world import CombatState, Position

@dataclass
class Action:
    action_type: ActionType
    target: Combatant
    weapon: Optional[Weapon] = None
    spell: Optional[Spell] = None
    rationale: str = ""

    @property
    def required_range(self) -> int:
        if self.weapon is not None:
            return self.weapon.range
        if self.spell is not None:
            return self.spell.range
        return 5

@dataclass
class ActionResult:
    action_type: ActionType
    target: Combatant
    actor: str = ""
    weapon: str = ""
    spell: str = ""
    amount: int = 0
    mitigated_amount: int = 0
    damage_type: Optional[DamageType] = None
    is_healing: bool = False
    concentration: bool = False
    spell_level: int = 0
    attack_result: AttackResult = AttackResult.MISS
    target_hp_after_action: int = 0
    combatant_x: int = 0
    combatant_y: int = 0
    target_x: int = 0
    target_y: int = 0
    save_made: bool = False
    effect_applied: str = ""
    rationale: str = ""
    attack_roll_bonus: Optional[int] = None
    save_ability: Optional[Ability] = None
    save_dc: Optional[int] = None
    save_succeeded: Optional[bool] = None

@dataclass
class SpellHitResult:
    target: Combatant
    attack_result: AttackResult
    amount: int
    mitigated_amount: int = 0
    save_made: bool = False
    effect_applied: str = ""
    attack_roll_bonus: Optional[int] = None
    save_ability: Optional[Ability] = None
    save_dc: Optional[int] = None
    save_succeeded: Optional[bool] = None

def is_auto_crit_attack(target: Combatant, weapon: Weapon) -> bool:
    return isinstance(weapon, MeleeWeapon) and any(e.auto_crit_in_melee for e in target.effects)

def attack_roll_bonus_observed(actor: Combatant, target: Combatant, weapon: Weapon) -> Optional[int]:
    if is_auto_crit_attack(target, weapon):
        return None
    return actor.get_attack_bonus(weapon)

def spell_flat_bonus(actor: Combatant, spell: Spell) -> int:
    # RAW: a spell adds no caster bonus to its damage unless it says so (e.g. Magic Missile's +1 per dart); healing spells add the spellcasting modifier.
    if spell.is_healing:
        return actor.ability_scores.modifier_for(actor.spellcasting_ability)
    return spell.damage_bonus

def move_towards_target(actor: Combatant, target: Combatant, combat_state: CombatState) -> list[ActionResult]:
    results = []

    distances_before_move = {
        other: combat_state.grid.distance(actor, other)
        for other in combat_state.initiative_order
        if other.team != actor.team and other.alive
    }

    new_position = combat_state.grid.move_towards(actor, target)
    actor.movement -= 5

    results.append(ActionResult(
        action_type = ActionType.MOVE,
        target = target,
        combatant_x = new_position.x,
        combatant_y = new_position.y
    ))

    if not actor.can_fly:
        for reactor, distance_before_move in distances_before_move.items():
            if not actor.alive or not reactor.has_reaction:
                continue

            melee_weapon = next((w for w in reactor.weapons if isinstance(w, MeleeWeapon)), None)
            if melee_weapon is None:
                continue

            was_in_reach = distance_before_move <= melee_weapon.reach
            still_in_reach = combat_state.grid.distance(actor, reactor) <= melee_weapon.reach

            if was_in_reach and not still_in_reach:
                reactor.has_reaction = False
                attack_result, amount, mitigated_amount = attack(reactor, actor, melee_weapon, combat_state)
                reactor_position = combat_state.grid.position_of(reactor)
                results.append(ActionResult(
                    action_type = ActionType.ATTACK,
                    target = actor,
                    actor = reactor.name,
                    weapon = melee_weapon.name,
                    amount = amount,
                    mitigated_amount = mitigated_amount,
                    damage_type = melee_weapon.damage_type,
                    attack_result = attack_result,
                    attack_roll_bonus = attack_roll_bonus_observed(reactor, actor, melee_weapon),
                    target_hp_after_action = actor.hp,
                    combatant_x = reactor_position.x,
                    combatant_y = reactor_position.y,
                    target_x = new_position.x,
                    target_y = new_position.y,
                    rationale = "Opportunity attack"
                ))
    
    return results

def attack(actor: Combatant, target: 'Combatant', weapon: Weapon, combat_state: CombatState) -> tuple[AttackResult, int, int]:
    attack_bonus = actor.get_attack_bonus(weapon)
    damage = 0

    advantage, disadvantage = resolve_advantage(actor, RollType.ATTACK, other = target, weapon = weapon, combat_state = combat_state)

    if is_auto_crit_attack(target, weapon):
        attack_result = AttackResult.CRIT
    else:
        attack_result = attack_roll(attack_bonus, target.ac, advantage, disadvantage)

    if attack_result == AttackResult.MISS:
        return attack_result, damage, 0

    damage = damage_roll(weapon.damage_dice, weapon.damage_sides, actor.get_damage_bonus(weapon), attack_result == AttackResult.CRIT)

    mitigated_amount = target.take_damage(damage, weapon.damage_type)

    return attack_result, damage, mitigated_amount

def determine_targets(target: Combatant, spell: Spell, combat_state: CombatState) -> list[Combatant]:
    combatants = []

    combatants.append(target)

    if spell.aoe_radius > 0:
        combatants.extend(combat_state.grid.combatants_in_range(target, spell.aoe_radius))

    return combatants

def cast_spell(actor: Combatant, target: Combatant, spell: Spell, combat_state: CombatState) -> list[SpellHitResult]:
    if not spell.is_cantrip:
        actor.spell_slots[spell.level] -= 1
    
    results = []

    targets = determine_targets(target, spell, combat_state)

    if spell.requires_attack_roll:
        for t in targets:
            for _ in range(spell.ray_count):
                results.append(resolve_spell_against_target(actor, t, spell, combat_state))
    else:
        damage_dice_used = spell.damage_dice + (1 if spell.is_cantrip and actor.caster_level >= 5 else 0)
        amount = damage_roll(damage_dice_used, spell.damage_sides, spell_flat_bonus(actor, spell), is_crit = False)
        for t in targets:
            results.append(resolve_spell_against_target(actor, t, spell, combat_state, amount))

    return results

def resolve_spell_against_target(actor: Combatant, target: Combatant, spell: Spell, combat_state: CombatState, amount: int = 0) -> SpellHitResult:
    attack_bonus = actor.get_spell_attack_bonus()
    damage = 0
    mitigated_amount = 0
    save_made = False
    effect_applied = ""
    observed_attack_bonus = None
    observed_save_ability = None
    observed_save_dc = None
    observed_save_succeeded = None

    if spell.requires_attack_roll:
        observed_attack_bonus = attack_bonus
        advantage, disadvantage = resolve_advantage(actor, RollType.ATTACK, other = target, combat_state = combat_state)
        attack_result = attack_roll(attack_bonus, target.ac, advantage, disadvantage)
    else:
        attack_result = AttackResult.HIT

    if amount == 0:
        if attack_result != AttackResult.MISS:
            damage_dice_used = spell.damage_dice

            if spell.is_cantrip:
                damage_dice_used += 1 if actor.caster_level >=5 else 0
        else:
            damage_dice_used = spell.damage_dice_on_miss

        damage = damage_roll(damage_dice_used, spell.damage_sides, spell_flat_bonus(actor, spell), attack_result == AttackResult.CRIT)
    else:
        damage = amount

    if spell.save_allowed:
        advantage, disadvantage = resolve_advantage(target, RollType.SAVE, other = actor, ability = spell.save_attribute, spell = spell, combat_state = combat_state)
        auto_failed = any(e.auto_fails_save(spell.save_attribute) for e in target.effects)
        save_succeeded = saving_throw(target, spell.save_attribute, actor.spell_save_dc, advantage, disadvantage)
        if not auto_failed:
            observed_save_ability = spell.save_attribute
            observed_save_dc = actor.spell_save_dc
            observed_save_succeeded = save_succeeded
        if save_succeeded:
            save_made = True
            damage = int(damage * spell.damage_pct_on_save)
            
    if damage > 0:
        if spell.is_healing:
            target.heal(damage)
            mitigated_amount = damage
        else:
            mitigated_amount = target.take_damage(damage, spell.damage_type)

    if spell.effect is not None:
        if (not spell.requires_attack_roll or attack_result != AttackResult.MISS) and (not spell.save_allowed or not save_made):
            new_effect = spell.effect(save_dc = actor.spell_save_dc, source = actor)
            target.add_effect(new_effect)
            effect_applied = spell.effect.name
            if spell.concentration:
                for existing in list(actor.effects):
                    if isinstance(existing, Concentrating):
                        actor.remove_effect(existing)
                actor.add_effect(Concentrating(maintained_effect = new_effect, maintained_target = target))
        else:
            save_made = True

    return SpellHitResult(target, attack_result, damage, mitigated_amount, save_made, effect_applied, observed_attack_bonus, observed_save_ability, observed_save_dc, observed_save_succeeded)