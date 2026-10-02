from typing import Optional

from enums import AttackResult, ActionType, TargetType
from combatant import Combatant, Monster, PlayerCharacter, Weapon, MeleeWeapon, RangedWeapon, Spell, Ability
from effects import Effect, AcidArrow, Barkskin, Blind, Concentrating, Paralysed
from world import CombatState, Position
from actions import Action, ActionResult, SpellHitResult, move_towards_target, attack, cast_spell, determine_targets
from policy import Policy
from policy_greedyutility import GreedyUtilityPolicy
from belief import CombatantBelief
from ai_profile import AIProfile, CreatureAIProfile, PlayerAIProfile

class CombatantAI:
    combatant: Combatant
    policy: Policy
    beliefs: dict[Combatant, CombatantBelief]
    profile: AIProfile

    def __init__(self, combatant: Combatant):
        self.combatant = combatant
        self.policy = GreedyUtilityPolicy()
        self.beliefs = {}
        if isinstance(combatant, Monster):
            self.profile = CreatureAIProfile()
        elif isinstance(combatant, PlayerCharacter):
            self.profile = PlayerAIProfile()
        else:
            self.profile = AIProfile()

    def reset(self) -> None:
        # Beliefs are per-encounter learned state -- each new combat is a fresh encounter with no
        # memory of unrelated previous ones, even when the same object instances are reused across
        # repeated Monte Carlo trials. policy/profile are deliberate, persistent configuration and
        # are left untouched.
        self.beliefs = {}

    def take_turn(self, combat_state: CombatState) -> list[ActionResult]:
        results = []

        for e in self.combatant.effects:
            if e.prevent_turn:
                results.append(self.make_result(Action(ActionType.NONE, self.combatant, rationale = e.name), AttackResult.MISS, 0, combat_state))
                return results

        if self.combatant.has_action:
            action = self.policy.decide(self.combatant, combat_state, self.beliefs, bonus_action = False)

            if action.action_type == ActionType.NONE:
                results.append(self.make_result(Action(ActionType.NONE, self.combatant, rationale = ""), AttackResult.MISS, 0, combat_state))
            else:
                self.move_and_execute(action, combat_state, results, bonus_action = False)

            self.combatant.has_action = False

        if self.combatant.has_bonus_action:
            bonus_action = self.policy.decide(self.combatant, combat_state, self.beliefs, bonus_action = True)

            if bonus_action.action_type == ActionType.NONE:
                results.append(self.make_result(Action(ActionType.NONE, self.combatant, rationale = ""), AttackResult.MISS, 0, combat_state))
            else:
                self.move_and_execute(bonus_action, combat_state, results, bonus_action = True)

            self.combatant.has_bonus_action = False

        return results

    def move_and_execute(self, action: Action, combat_state: CombatState, results: list, bonus_action: bool) -> None:
        while (self.combatant.movement > 0 and
               combat_state.grid.distance(self.combatant, action.target) > action.required_range
               and not any(e.forbids_approaching(action.target) for e in self.combatant.effects)):
            results.extend(move_towards_target(self.combatant, action.target, combat_state))

        if combat_state.grid.distance(self.combatant, action.target) <= action.required_range:
            results.extend(self.execute(action, combat_state, bonus_action))

    def execute(self, action: Action, combat_state: CombatState, bonus_action: bool = False) -> list[ActionResult]:
        results = []

        match action.action_type:
            case ActionType.SPELL:
                if action.spell is None:
                    return results
                
                if combat_state.grid.distance(self.combatant, action.target) <= action.required_range:
                    spell_hit_results = cast_spell(self.combatant, action.target, action.spell, combat_state)
                    for shr in spell_hit_results:
                        results.append(self.make_result(action, shr.attack_result, shr.amount, combat_state, target = shr.target, save_made = shr.save_made, mitigated_amount = shr.mitigated_amount))

            case ActionType.ATTACK:
                number_of_attacks = 1
                if not bonus_action:
                    number_of_attacks = self.combatant.attack_count

                for _ in range(number_of_attacks):
                    if not action.target.alive:
                        _, new_action = self.policy.best_attack(self.combatant, combat_state, self.beliefs, bonus_action)
                        if new_action is None:
                            break
                        action = new_action
                        while self.combatant.movement > 0 and combat_state.grid.distance(self.combatant, action.target) > action.required_range:
                            results.extend(move_towards_target(self.combatant, action.target, combat_state))

                    if action.weapon is None:
                        return results
         
                    if combat_state.grid.distance(self.combatant, action.target) <= action.required_range:
                        attack_result, amount, mitigated_amount = attack(self.combatant, action.target, action.weapon, combat_state)
                        results.append(self.make_result(action, attack_result, amount, combat_state, mitigated_amount = mitigated_amount))

            case ActionType.NONE:
                results.append(ActionResult(
                    action_type = ActionType.NONE,
                    target = self.combatant
                ))

        return results
    
    def make_result(self, action: Action, attack_result: AttackResult, amount: int, combat_state: CombatState, target: Optional[Combatant] = None, save_made: bool = False, effect_applied: str = "", mitigated_amount: int = 0) -> ActionResult:
        combatant_position = combat_state.grid.position_of(self.combatant)
        target_position = combat_state.grid.position_of(target) if target is not None else combat_state.grid.position_of(action.target)

        return ActionResult(
            action_type = action.action_type,
            target = target if target is not None else action.target,
            actor = self.combatant.name,
            spell = action.spell.name if action.spell else "",
            weapon = action.weapon.name if action.weapon else "",
            amount = amount,
            mitigated_amount = mitigated_amount,
            damage_type = action.weapon.damage_type if action.weapon else (action.spell.damage_type if action.spell else None),
            is_healing = action.spell.is_healing if action.spell else False,
            concentration = action.spell.concentration if action.spell else False,
            spell_level = action.spell.level if action.spell else 0,
            attack_result = attack_result,
            target_hp_after_action = target.hp if target is not None else action.target.hp,
            combatant_x = combatant_position.x,
            combatant_y = combatant_position.y,
            target_x = target_position.x,
            target_y = target_position.y,
            save_made = save_made,
            effect_applied = effect_applied,
            rationale = action.rationale
        )