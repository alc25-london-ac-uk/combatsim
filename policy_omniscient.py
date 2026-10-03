from belief import CombatantBelief
from combatant import Combatant
from policy_utility import UtilityPolicy

class OmniscientPolicy(UtilityPolicy):
    """Opponents are represented by their true current state."""

    def _belief_for(self, target: Combatant, beliefs: dict[Combatant, CombatantBelief]) -> CombatantBelief:
        return CombatantBelief.ground_truth_for(target)
