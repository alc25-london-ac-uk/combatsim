import pytest

from policy import Policy
from policy_utility import UtilityPolicy
from policy_random import RandomPolicy
from policy_greedyutility import GreedyUtilityPolicy
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_omniscient import OmniscientPolicy

SCORING_POLICIES = [GreedyUtilityPolicy, BeliefUpdatingPolicy, OmniscientPolicy]

def test_every_policy_is_a_policy():
    for policy_class in SCORING_POLICIES + [RandomPolicy]:
        assert issubclass(policy_class, Policy)

def test_the_three_scoring_policies_share_one_scorer_through_utility_policy():
    for policy_class in SCORING_POLICIES:
        assert issubclass(policy_class, UtilityPolicy)

def test_the_scoring_policies_are_siblings_not_parents_and_children():
    for policy_class in SCORING_POLICIES:
        for other in SCORING_POLICIES:
            if policy_class is not other:
                assert not issubclass(policy_class, other)

def test_random_policy_does_not_inherit_the_scoring_machinery():
    assert not issubclass(RandomPolicy, UtilityPolicy)

def test_utility_policy_cannot_be_used_without_saying_what_is_believed_about_opponents():
    with pytest.raises(TypeError):
        UtilityPolicy()

def test_the_scoring_policies_differ_only_in_how_they_form_beliefs():
    for policy_class in SCORING_POLICIES:
        overridden = {name for name in vars(policy_class) if not name.startswith("__") and name not in ("_fixed_guesses",)}
        assert "_belief_for" in overridden
        assert not overridden & {"score_attack", "score_spell", "score_spell_hit", "decide", "best_attack", "best_spell"}
