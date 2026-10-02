from combatant import Combatant
from belief import CombatantBelief
from policy_beliefupdating import BeliefUpdatingPolicy

class OmniscientPolicy(BeliefUpdatingPolicy):
    def _belief_for(self, target: Combatant, beliefs: dict[Combatant, CombatantBelief]) -> CombatantBelief:
        return CombatantBelief.ground_truth_for(target)
