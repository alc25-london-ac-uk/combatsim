from abc import ABC, abstractmethod
from typing import Optional

from actions import Action
from world import CombatState
from combatant import Combatant
from belief import CombatantBelief

class Policy(ABC):
    @abstractmethod
    def decide(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> Action:
        pass

    @abstractmethod
    def best_attack(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        pass