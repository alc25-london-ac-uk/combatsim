from ai_profile import CreatureAIProfile
from enums import TargetPriority

def test_creature_ai_profile_defaults_to_weakest_target_priority():
    assert CreatureAIProfile().target_priority == TargetPriority.WEAKEST

def test_creature_ai_profile_target_priority_is_overridable():
    profile = CreatureAIProfile(target_priority = TargetPriority.HIGHEST_THREAT)

    assert profile.target_priority == TargetPriority.HIGHEST_THREAT

def test_creature_ai_profile_carries_only_the_target_priority():
    assert set(vars(CreatureAIProfile())) == {"target_priority"}

def test_target_priority_has_exactly_the_three_documented_options():
    assert {p.name for p in TargetPriority} == {"NEAREST", "WEAKEST", "HIGHEST_THREAT"}
