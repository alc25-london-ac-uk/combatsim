from abc import ABC, abstractmethod
from typing import Optional

from actions import Action
from world import CombatState
from combatant import Combatant
from belief import CombatantBelief
from enums import Horizon

class Policy(ABC):
    @abstractmethod
    def decide(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> Action:
        pass

    @abstractmethod
    def best_attack(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        pass

    def _horizon_penalty(self, combatant: Combatant, combat_state: CombatState, exposed_to_melee: bool) -> float:
        if combatant.ai.profile.tactical_horizon != Horizon.ONE:
            return 0.0
        if not exposed_to_melee:
            return 0.0

        worst_case_damage = 0.0
        for enemy in combat_state.initiative_order:
            if not enemy.alive or enemy.team == combatant.team:
                continue
            for weapon in enemy.weapons:
                hit_probability = max(0, min(1, (21 - (combatant.ac - enemy.get_attack_bonus(weapon))) / 20))
                expected_damage = hit_probability * (
                    weapon.damage_dice * (weapon.damage_sides + 1) / 2
                    + enemy.get_damage_bonus(weapon)
                )
                worst_case_damage = max(worst_case_damage, expected_damage)

        return -worst_case_damage