import random
from typing import Optional

from enums import TargetType, ActionType
from weapon import MeleeWeapon
from actions import Action
from world import CombatState
from combatant import Combatant
from policy import Policy
from belief import CombatantBelief

class RandomPolicy(Policy):
    def decide(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> Action:
        action_candidates = [
            self.best_spell(combatant, combat_state, bonus_action),
            self.best_attack(combatant, combat_state, beliefs, bonus_action)
        ]

        valid_candidates = [action for _, action in action_candidates if action is not None]
        if not valid_candidates:
            return Action(ActionType.NONE, combatant)

        return random.choice(valid_candidates)

    def best_attack(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        candidates = []

        for target in combat_state.initiative_order:
            if target.alive and target.team != combatant.team:
                for weapon in combatant.weapons:
                    if (isinstance(weapon, MeleeWeapon) and weapon.is_off_hand) == bonus_action:
                        candidates.append(Action(ActionType.ATTACK, target, rationale = "random", weapon = weapon))

        if not candidates:
            return -1.0, None

        return random.random(), random.choice(candidates)

    def best_spell(self, combatant: Combatant, combat_state: CombatState, bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        candidates = []

        for target in combat_state.initiative_order:
            if target.alive:
                for spell in combatant.spells:
                    if spell.is_bonus_action == bonus_action and (spell.is_cantrip or combatant.spell_slots.get(spell.level, 0) > 0):
                        if (spell.target_type == TargetType.ENEMY and target.team != combatant.team) or (spell.target_type == TargetType.ALLY and target.team == combatant.team):
                            candidates.append(Action(ActionType.SPELL, target, rationale = "random", spell = spell))

        if not candidates:
            return -1.0, None

        return random.random(), random.choice(candidates)
