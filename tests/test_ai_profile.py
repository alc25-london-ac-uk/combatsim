from ai_profile import AIProfile, CreatureAIProfile, PlayerAIProfile
from enums import Horizon, TargetPriority, PartyRole

# --- AIProfile ---

def test_ai_profile_defaults_to_horizon_none():
    profile = AIProfile()

    assert profile.tactical_horizon == Horizon.NONE

def test_ai_profile_fields_are_independently_overridable():
    profile = AIProfile(aggression = 0.9, self_preservation = 0.1, threat_weighting = 0.7, tactical_horizon = Horizon.ONE)

    assert profile.aggression == 0.9
    assert profile.self_preservation == 0.1
    assert profile.threat_weighting == 0.7
    assert profile.tactical_horizon == Horizon.ONE

# --- CreatureAIProfile ---

def test_creature_ai_profile_inherits_the_base_fields():
    profile = CreatureAIProfile()

    assert profile.aggression == 0.5
    assert profile.tactical_horizon == Horizon.NONE

def test_creature_ai_profile_defaults_to_weakest_target_priority():
    profile = CreatureAIProfile()

    assert profile.target_priority == TargetPriority.WEAKEST

def test_creature_ai_profile_target_priority_is_overridable():
    profile = CreatureAIProfile(target_priority = TargetPriority.HIGHEST_THREAT)

    assert profile.target_priority == TargetPriority.HIGHEST_THREAT

# --- PlayerAIProfile ---

def test_player_ai_profile_inherits_the_base_fields():
    profile = PlayerAIProfile()

    assert profile.aggression == 0.5
    assert profile.tactical_horizon == Horizon.NONE

def test_player_ai_profile_defaults_to_damage_party_role():
    profile = PlayerAIProfile()

    assert profile.party_role == PartyRole.DAMAGE

def test_player_ai_profile_party_role_is_overridable():
    profile = PlayerAIProfile(party_role = PartyRole.SUPPORT)

    assert profile.party_role == PartyRole.SUPPORT

# --- CreatureAIProfile / PlayerAIProfile are distinct, independent specialisations ---

def test_creature_and_player_profiles_do_not_share_fields_with_each_other():
    creature = CreatureAIProfile()
    player = PlayerAIProfile()

    assert not hasattr(creature, "party_role")
    assert not hasattr(player, "target_priority")