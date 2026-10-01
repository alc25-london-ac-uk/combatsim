from typing import Optional

from enums import TargetType
from weapon import Weapon, MeleeWeapon, RangedWeapon
from spell import Spell
from effects import Concentrating
from actions import ActionType, Action, determine_targets
from world import CombatState
from combatant import Combatant
from policy import Policy
from belief import CombatantBelief

HEALER_PRIORITY_WEIGHT = 1.5
CONCENTRATION_PRIORITY_WEIGHT = 1.0
OFFENSIVE_PRIORITY_WEIGHT = 0.5

class BeliefUpdatingPolicy(Policy):
    def _priority_bonus(self, belief: CombatantBelief) -> float:
        remaining_resource_confidence = 1 - belief.depleted
        return (
            belief.healer_capable * remaining_resource_confidence * HEALER_PRIORITY_WEIGHT
            + belief.concentrating * CONCENTRATION_PRIORITY_WEIGHT
            + belief.offensive_capable * remaining_resource_confidence * OFFENSIVE_PRIORITY_WEIGHT
        )

    def decide(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> Action:
        action_candidates = [
            self.best_spell(combatant, combat_state, beliefs, bonus_action),
            self.best_attack(combatant, combat_state, beliefs, bonus_action)
        ]

        best_score, best_action = max(action_candidates, key = lambda c: c[0])

        if best_action is not None:
            combined_rationale = " | ".join(
                action.rationale
                for _, action in action_candidates
                if action is not None
            )
            best_action.rationale = f"{best_action.rationale} [vs: {combined_rationale}]"

        return best_action or Action(ActionType.NONE, combatant)

    def best_attack(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        best_score = -1.0
        best_action = None

        for target in combat_state.initiative_order:
            if target.alive:
                if target.team != combatant.team:
                    for weapon in combatant.weapons:
                        if (isinstance(weapon, MeleeWeapon) and weapon.is_off_hand) == bonus_action:
                            score = self.score_attack(combatant, target, weapon, combat_state, beliefs)
                            if score > best_score:
                                best_score = score
                                best_action = Action(ActionType.ATTACK, target, rationale = f"attack score: {score:.2f}", weapon = weapon)

        return best_score, best_action

    def score_attack(self, combatant: Combatant, target: Combatant, weapon: Weapon, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> float:
        hit_probability = max(0, min(1,
            (21 - (target.ac - combatant.get_attack_bonus(weapon))) / 20
        ))

        if isinstance(weapon, RangedWeapon) and combat_state.grid.enemies_in_melee_range(combatant):
            hit_probability *= 0.5

        expected_damage = hit_probability * (
            weapon.damage_dice * (weapon.damage_sides + 1) / 2
            + combatant.get_damage_bonus(weapon)
        )

        belief = beliefs.setdefault(target, CombatantBelief.initial_prior_for(target))
        expected_damage *= belief.damage_multiplier(weapon.damage_type)
        kill_bonus = belief.probability_at_or_below(round(expected_damage)) * 2.0
        priority_bonus = self._priority_bonus(belief)

        distance = combat_state.grid.distance(combatant, target)
        movement_penalty = max(0, distance - weapon.range) / combatant.speed
        if any(e.forbids_approaching(target) for e in combatant.effects):
            movement_penalty = 100

        return expected_damage + kill_bonus + priority_bonus - movement_penalty

    def best_spell(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        best_score = -1.0
        best_action = None

        for target in combat_state.initiative_order:
            if target.alive:
                for spell in combatant.spells:
                    if spell.is_bonus_action == bonus_action:
                        if (spell.target_type == TargetType.ENEMY and target.team != combatant.team) or (spell.target_type == TargetType.ALLY and target.team == combatant.team):
                            score = self.score_spell(combatant, target, spell, combat_state, beliefs)
                            if score > best_score:
                                best_score = score
                                best_action = Action(ActionType.SPELL, target, rationale = f"spell score: {score:.2f}", spell = spell)

        return best_score, best_action

    def score_spell(self, combatant: Combatant, target: Combatant, spell: Spell, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> float:
        if combatant.spell_slots.get(spell.level, 0) == 0:
            return -1.0

        distance = combat_state.grid.distance(combatant, target)
        movement_penalty = max(0, distance - spell.range) / combatant.speed
        if any(e.forbids_approaching(target) for e in combatant.effects):
            movement_penalty = 100

        concentration_penalty = 3.0 if spell.concentration and combatant.has_effect(Concentrating) else 0.0

        targets = determine_targets(target, spell, combat_state)
        total = sum(self.score_spell_hit(combatant, t, spell, combat_state, beliefs) for t in targets)

        return total - movement_penalty - concentration_penalty

    def score_spell_hit(self, combatant: Combatant, target: Combatant, spell: Spell, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> float:
        is_ally = target.team == combatant.team
        belief = beliefs.setdefault(target, CombatantBelief.initial_prior_for(target))
        believed_hp_fraction = belief.expected_hp() / belief.believed_max_hp if belief.believed_max_hp > 0 else 0.0

        if spell.is_healing:
            if not is_ally:
                return -1.0

            expected_healing = (1 + 8) / 2 + combatant.ability_scores.modifier_for(combatant.spellcasting_ability)
            urgency = 1 - believed_hp_fraction

            return expected_healing * urgency

        if spell.effect is not None and spell.damage_dice == 0:
            threat = believed_hp_fraction
            score = 5.0 * threat

            return -score if is_ally else score + self._priority_bonus(belief)

        if not spell.requires_attack_roll:
            hit_probability = 1
        else:
            hit_probability = max(0, min(1, (21 - (target.ac - combatant.get_spell_attack_bonus())) / 20))

        expected_damage = hit_probability * (
            (spell.damage_dice + 1 if combatant.caster_level >= 5 else 0) * (spell.damage_sides + 1) / 2
            + combatant.ability_scores.modifier_for(combatant.spellcasting_ability)
        )

        if spell.save_allowed:
            save_mod = target.ability_scores.modifier_for(spell.save_attribute)
            save_success_probability = max(0, min(1,
                (21 - (combatant.spell_save_dc - save_mod)) / 20
            ))
            expected_damage = (
                expected_damage * (1 - save_success_probability) +
                expected_damage * spell.damage_pct_on_save * save_success_probability
            )

        if spell.damage_type is not None:
            expected_damage *= belief.damage_multiplier(spell.damage_type)

        kill_bonus = belief.probability_at_or_below(round(expected_damage)) * 2.0
        priority_bonus = self._priority_bonus(belief)

        return -expected_damage if is_ally else (expected_damage + kill_bonus + priority_bonus)