from typing import Optional, Union
import random
from enum import Enum, auto
from dataclasses import dataclass, field

from enums import AttackResult, ActionType
from combatant import Combatant, Weapon, MeleeWeapon, RangedWeapon, Spell, Ability
from effects import Effect, AcidArrow, Barkskin, Blind, Concentrating, Paralysed
from world import CombatState, Position
from actions import Action, ActionResult, move_towards_target, attack, heal, cast_spell

class CombatantAI:
    combatant: Combatant

    def __init__(self, combatant: Combatant):
        self.combatant = combatant

    # TODO: bonus actions
    # TODO: reactions
    def take_turn(self, combat_state: CombatState) -> list[ActionResult]:
        results = []

        if self.combatant.has_effect(Paralysed):
            results.append(self.make_result(Action(ActionType.NONE, self.combatant, rationale = "Paralysed"), AttackResult.MISS, 0, combat_state))
            return results

        action = self.decide(combat_state)

        if action.action_type == ActionType.NONE:
            results.append(self.make_result(Action(ActionType.NONE, self.combatant, rationale = ""), AttackResult.MISS, 0, combat_state))
            return results

        while (self.combatant.movement > 0 and
                combat_state.grid.distance(self.combatant, action.target) > action.required_range):
            results.append(move_towards_target(self.combatant, action.target, combat_state))
        
        if combat_state.grid.distance(self.combatant, action.target) <= action.required_range:
            results.extend(self.execute(action, combat_state))

        return results
    
    def decide(self, combat_state: CombatState) -> Action:
        best_score = -1.0
        best_action = None

        action_candidates = [
            self.best_heal(combat_state),
            self.best_spell(combat_state),
            self.best_attack(combat_state)
        ]

        best_score, best_action = max(action_candidates, key = lambda c: c[0])

        if best_action is not None:
            combined_rationale = " | ".join(
                action.rationale
                for _, action in action_candidates
                if action is not None
            )
            best_action.rationale = f"{best_action.rationale} [vs: {combined_rationale}]"

        return best_action or Action(ActionType.NONE, self.combatant)
    
    def best_heal(self, combat_state: CombatState) -> tuple[float, Optional[Action]]:
        best_score = -1.0
        best_action = None

        for target in combat_state.initiative_order:
            if target.alive:
                if target.team == self.combatant.team:
                    score = self.score_heal(target, combat_state)
                    if score > best_score:
                        best_score = score
                        best_action = Action(ActionType.HEAL, target, rationale = f"heal score: {score:.2f}")
        
        return best_score, best_action

    def best_spell(self, combat_state: CombatState) -> tuple[float, Optional[Action]]:
        best_score = -1.0
        best_action = None

        for target in combat_state.initiative_order:
            if target.alive:
                if target.team != self.combatant.team:
                    for spell in self.combatant.spells:
                        score = self.score_spell(target, spell, combat_state)
                        if score > best_score:
                            best_score = score
                            best_action = Action(ActionType.SPELL, target, rationale = f"spell score: {score:.2f}", spell = spell)

        return best_score, best_action

    def best_attack(self, combat_state: CombatState) -> tuple[float, Optional[Action]]:
        best_score = -1.0
        best_action = None

        for target in combat_state.initiative_order:
            if target.alive:
                if target.team != self.combatant.team:
                    for weapon in self.combatant.weapons:
                        score = self.score_attack(target, weapon, combat_state)
                        if score > best_score:
                            best_score = score
                            best_action = Action(ActionType.ATTACK, target, rationale = f"attack score: {score:.2f}", weapon = weapon)
        
        return best_score, best_action

    def score_heal(self, target: Combatant, combat_state: CombatState) -> float:
        if self.combatant.spell_slots.get(1, 0) == 0:
            return -1.0

        expected_healing = (1 + 8) / 2 + self.combatant.ability_scores.modifier_for(self.combatant.spellcasting_ability)
        urgency = 1 - (target.hp / target.max_hp)
        distance = combat_state.grid.distance(self.combatant, target)
        movement_penalty = max(0, distance - 5) / self.combatant.speed

        return (expected_healing * urgency) - movement_penalty
    
    def score_attack(self, target: Combatant, weapon: Weapon, combat_state: CombatState) -> float:
        hit_probability = max(0, min(1,
            (21 - (target.ac - self.combatant.get_attack_bonus(weapon))) / 20
        ))
        expected_damage = hit_probability * (
            weapon.damage_dice * (weapon.damage_sides + 1) / 2
            + self.combatant.get_damage_bonus(weapon)
        )
        kill_bonus = min(1, expected_damage / max(1, target.hp)) * 2.0
        distance = combat_state.grid.distance(self.combatant, target)
        movement_penalty = max(0, distance - weapon.range) / self.combatant.speed

        return expected_damage + kill_bonus - movement_penalty
    
    def score_spell(self, target: Combatant, spell: Spell, combat_state: CombatState) -> float:
        if self.combatant.spell_slots.get(spell.level, 0) == 0:
            return -1.0

        # control spells
        if spell.effect is not None and spell.damage_dice == 0:
            threat = target.hp / target.max_hp
            distance = combat_state.grid.distance(self.combatant, target)
            movement_penalty = max(0, distance - spell.range) / self.combatant.speed
            return (5.0 * threat) - movement_penalty

        # damage spells
        if not spell.requires_attack_roll:
            hit_probability = 1
        else:
            hit_probability = max(0, min(1,
                (21 - (target.ac - self.combatant.get_spell_attack_bonus())) / 20
            ))
        expected_damage = hit_probability * (
            spell.damage_dice * (spell.damage_sides + 1) / 2
            + self.combatant.ability_scores.modifier_for(self.combatant.spellcasting_ability)
        )
        if spell.save_allowed:
            save_mod = target.ability_scores.modifier_for(spell.save_attribute)
            save_success_probability = max(0, min(1,
                (21 - (self.combatant.spell_save_dc - save_mod)) / 20
            ))
            expected_damage = (
                expected_damage * (1 - save_success_probability) +
                expected_damage * spell.damage_pct_on_save * save_success_probability
            )
        kill_bonus = min(1, expected_damage / max(1, target.hp)) * 2.0
        distance = combat_state.grid.distance(self.combatant, target)
        movement_penalty = max(0, distance - spell.range) / self.combatant.speed

        return expected_damage + kill_bonus - movement_penalty

    def execute(self, action: Action, combat_state: CombatState) -> list[ActionResult]:
        results = []

        match action.action_type:
            case ActionType.HEAL:
                if combat_state.grid.distance(self.combatant, action.target) <= 5:            
                    amount = heal(self.combatant, action.target)
                    results.append(self.make_result(action, AttackResult.HIT, amount, combat_state))

            case ActionType.SPELL:
                if action.spell is None:
                    return results
                
                if combat_state.grid.distance(self.combatant, action.target) <= action.required_range:
                    attack_result, amount, save_made, effect_applied = cast_spell(self.combatant, action.target, action.spell)
                    results.append(self.make_result(action, attack_result, amount, combat_state, save_made = save_made))

            case ActionType.ATTACK:
                for _ in range(self.combatant.attack_count):
                    if not action.target.alive:
                        _, new_action = self.best_attack(combat_state)
                        if new_action is None:
                            break
                        action = new_action
                        while self.combatant.movement > 0 and combat_state.grid.distance(self.combatant, action.target) > action.required_range:
                            results.append(move_towards_target(self.combatant, action.target, combat_state))

                    if action.weapon is None:
                        return results
         
                    if combat_state.grid.distance(self.combatant, action.target) <= action.required_range:
                        attack_result, amount = attack(self.combatant, action.target, action.weapon)
                        results.append(self.make_result(action, attack_result, amount, combat_state))

            case ActionType.NONE:
                results.append(ActionResult(
                    action_type = ActionType.NONE,
                    target = self.combatant
                ))

        return results
    
    def make_result(self, action: Action, attack_result: AttackResult, amount: int, combat_state: CombatState, save_made: bool = False, effect_applied: str = "") -> ActionResult:
        combatant_position = combat_state.grid.position_of(self.combatant)
        target_position = combat_state.grid.position_of(action.target)

        return ActionResult(
            action_type = action.action_type,
            target = action.target,
            spell = action.spell.name if action.spell else "",
            weapon = action.weapon.name if action.weapon else "",
            amount = amount,
            attack_result = attack_result,
            target_hp_after_action = action.target.hp,
            combatant_x = combatant_position.x,
            combatant_y = combatant_position.y,
            target_x = target_position.x,
            target_y = target_position.y,
            save_made = save_made,
            effect_applied = effect_applied,
            rationale = action.rationale
        )