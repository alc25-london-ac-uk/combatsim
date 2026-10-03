from belief import CombatantBelief, belief_for
from combatant import Combatant
from policy_utility import UtilityPolicy

class BeliefUpdatingPolicy(UtilityPolicy):
    """Opponents are represented by beliefs that are updated from everything observed during the fight."""

    def _belief_for(self, target: Combatant, beliefs: dict[Combatant, CombatantBelief]) -> CombatantBelief:
        return belief_for(beliefs, target)
