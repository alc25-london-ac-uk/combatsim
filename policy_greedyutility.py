from belief import CombatantBelief
from combatant import Combatant
from enums import Ability, DamageType
from policy_utility import UtilityPolicy

class GreedyUtilityPolicy(UtilityPolicy):
    def __init__(self):
        self._fixed_guesses: dict[Combatant, CombatantBelief] = {}

    def _belief_for(self, target: Combatant, beliefs: dict[Combatant, CombatantBelief]) -> CombatantBelief:
        if target not in self._fixed_guesses:
            self._fixed_guesses[target] = self._most_likely_state(target)
        return self._fixed_guesses[target]

    @staticmethod
    def _most_likely_state(target: Combatant) -> CombatantBelief:
        prior = CombatantBelief.initial_prior_for(target)
        assumed_hp = round(prior.believed_max_hp)

        def mode(distribution: dict[int, float]) -> int:
            return max(distribution, key = distribution.get)

        return CombatantBelief(
            hypotheses = {(assumed_hp, assumed_hp): 1.0},
            offensive_capable = 0.0,
            healer_capable = 0.0,
            concentrating = 0.0,
            depleted = 0.0,
            damage_multipliers = {damage_type: 1.0 for damage_type in DamageType},
            ac_distribution = {mode(prior.ac_distribution): 1.0},
            save_distributions = {ability: {mode(prior.save_modifier_distribution(ability)): 1.0} for ability in Ability},
        )
