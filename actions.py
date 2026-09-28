from typing import Optional
import random
from dataclasses import dataclass

from enums import AttackResult, ActionType, RollType
from dice import saving_throw, attack_roll, damage_roll, resolve_advantage
from combatant import Combatant, Weapon, MeleeWeapon, RangedWeapon, Spell, Ability
from effects import Effect, AcidArrow, Barkskin, Blind, Concentrating, Paralysed
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
    weapon: str = ""
    spell: str = ""
    amount: int = 0
    is_healing: bool = False
    attack_result: AttackResult = AttackResult.MISS
    target_hp_after_action: int = 0
    combatant_x: int = 0
    combatant_y: int = 0
    target_x: int = 0
    target_y: int = 0
    save_made: bool = False
    effect_applied: str = ""
    rationale: str = ""

def move_towards_target(actor: Combatant, target: Combatant, combat_state: CombatState) -> ActionResult:
    new_position = combat_state.grid.move_towards(actor, target)
    actor.movement -= 5
    return ActionResult(
        action_type = ActionType.MOVE,
        target = target,
        combatant_x = new_position.x,
        combatant_y = new_position.y
    )

def attack(actor: Combatant, target: 'Combatant', weapon: Weapon, combat_state: CombatState) -> tuple[AttackResult, int]:
    attack_bonus = actor.get_attack_bonus(weapon)
    damage = 0

    advantage, disadvantage = resolve_advantage(actor, RollType.ATTACK, other = target, weapon = weapon, combat_state = combat_state)
    
    if target.has_effect(Paralysed) and isinstance(weapon, MeleeWeapon):
        attack_result = AttackResult.CRIT
    else:
        attack_result = attack_roll(attack_bonus, target.ac, advantage, disadvantage)
    
    if attack_result == AttackResult.MISS:
        return attack_result, damage
    
    damage = damage_roll(weapon.damage_dice, weapon.damage_sides, actor.get_damage_bonus(weapon), attack_result == AttackResult.CRIT)

    target.hp -= damage

    for effect in target.effects:
        effect.on_damage_taken(target, damage)

    return attack_result, damage

def cast_spell(actor: Combatant, target: Combatant, spell: Spell, combat_state: CombatState) -> tuple[AttackResult, int, bool, str]:
    attack_bonus = actor.get_spell_attack_bonus()
    damage = 0
    save_made = False
    effect_applied = ""

    if spell.level > 0:
        actor.spell_slots[spell.level] -= 1

    if spell.requires_attack_roll:
        advantage, disadvantage = resolve_advantage(actor, RollType.ATTACK, other = target, combat_state = combat_state)
        attack_result = attack_roll(attack_bonus, target.ac, advantage, disadvantage)
    else:
        attack_result = AttackResult.HIT

    if attack_result != AttackResult.MISS:
        damage_dice_used = spell.damage_dice
    else:
        damage_dice_used = spell.damage_dice_on_miss

    damage = damage_roll(damage_dice_used, spell.damage_sides, attack_bonus, attack_result == AttackResult.CRIT)

    if spell.save_allowed:
        advantage, disadvantage = resolve_advantage(target, RollType.SAVE, other = actor, ability = spell.save_attribute, spell = spell, combat_state = combat_state)
        if saving_throw(target, spell.save_attribute, actor.spell_save_dc, advantage, disadvantage):
            save_made = True
            damage = int(damage * spell.damage_pct_on_save)
            
    if damage > 0:
        if spell.is_healing:
            target.heal(damage)
        else:
            target.take_damage(damage)

    if spell.effect is not None:
        if (not spell.requires_attack_roll or attack_result != AttackResult.MISS) and (not spell.save_allowed or not save_made):
            target.add_effect(spell.effect(save_dc = actor.spell_save_dc))
            effect_applied = spell.effect.name
            if spell.concentration:
                actor.add_effect(Concentrating())
        else:
            save_made = True

    return attack_result, damage, save_made, effect_applied