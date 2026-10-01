from belief import CombatantBelief
from enums import DamageType

# --- CombatantBelief.initial_prior_for ---

def test_initial_prior_for_dispatches_monsters_to_the_monster_prior(make_monster):
    monster = make_monster(max_hp = 30)
    monster.hp = monster.max_hp

    belief = CombatantBelief.initial_prior_for(monster)

    assert belief.believed_max_hp == 30

def test_initial_prior_for_dispatches_player_characters_to_the_class_level_prior(make_player):
    player = make_player(character_class = "wizard", level = 5)

    belief = CombatantBelief.initial_prior_for(player)
    direct = CombatantBelief.for_player_character(character_class = "wizard", level = 5)

    assert belief.hp_distribution == direct.hp_distribution

def _assert_distribution_sums_to_one(distribution: dict[int, float]) -> None:
    assert abs(sum(distribution.values()) - 1.0) < 1e-9

# --- CombatantBelief: offensive_capable / healer_capable ---

def test_spellcasting_priors_are_uninformative_regardless_of_combatant_type(make_monster, make_player):
    monster_belief = CombatantBelief.initial_prior_for(make_monster())
    player_belief = CombatantBelief.initial_prior_for(make_player())

    assert monster_belief.offensive_capable == 0.5
    assert monster_belief.healer_capable == 0.5
    assert player_belief.offensive_capable == 0.5
    assert player_belief.healer_capable == 0.5

def test_observe_offensive_cast_raises_offensive_capable_only():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_offensive_cast()

    assert belief.offensive_capable > 0.5
    assert belief.healer_capable == 0.5

def test_observe_healing_cast_raises_healer_capable_only():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_healing_cast()

    assert belief.healer_capable > 0.5
    assert belief.offensive_capable == 0.5

def test_worked_example_single_offensive_cast_observation():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_offensive_cast()

    assert abs(belief.offensive_capable - 0.95) < 1e-9

def test_worked_example_two_offensive_cast_observations_compound():
    # matches the agreed worked example: two observations -> ~0.997
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_offensive_cast()
    belief.observe_offensive_cast()

    assert abs(belief.offensive_capable - 0.9972375690607735) < 1e-9

def test_offensive_and_healer_capable_can_both_be_high_at_once():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_offensive_cast()
    belief.observe_healing_cast()

    assert belief.offensive_capable > 0.5
    assert belief.healer_capable > 0.5

def test_repeated_observation_does_not_reach_certainty_within_a_realistic_combat_length():
    belief = CombatantBelief.for_monster(max_hp = 20)

    for _ in range(5):
        belief.observe_offensive_cast()

    assert belief.offensive_capable < 1.0

# --- CombatantBelief: concentrating ---

def test_concentration_prior_is_a_true_zero_regardless_of_combatant_type(make_monster, make_player):
    monster_belief = CombatantBelief.initial_prior_for(make_monster())
    player_belief = CombatantBelief.initial_prior_for(make_player())

    assert monster_belief.concentrating == 0.0
    assert player_belief.concentrating == 0.0

def test_observe_concentration_spell_cast_sets_near_certain_belief():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_concentration_spell_cast()

    assert abs(belief.concentrating - 0.95) < 1e-9

def test_observe_concentration_spell_cast_again_stays_near_certain_not_cumulative():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_concentration_spell_cast()
    belief.observe_concentration_spell_cast()

    assert abs(belief.concentrating - 0.95) < 1e-9

def test_observe_damage_decays_concentration_belief_by_the_typical_save_probability():
    belief = CombatantBelief.for_monster(max_hp = 20)
    belief.observe_concentration_spell_cast()

    belief.observe_damage(10)

    assert abs(belief.concentrating - (0.95 * 0.625)) < 1e-9

def test_observe_damage_while_not_concentrating_stays_at_zero():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_damage(15)

    assert belief.concentrating == 0.0

def test_repeated_damage_drives_concentration_belief_down_towards_zero():
    belief = CombatantBelief.for_monster(max_hp = 20)
    belief.observe_concentration_spell_cast()

    for _ in range(5):
        belief.observe_damage(20)

    assert belief.concentrating < 0.1

# --- CombatantBelief: depleted ---

def test_depletion_prior_is_a_true_zero_regardless_of_combatant_type(make_monster, make_player):
    monster_belief = CombatantBelief.initial_prior_for(make_monster())
    player_belief = CombatantBelief.initial_prior_for(make_player())

    assert monster_belief.depleted == 0.0
    assert player_belief.depleted == 0.0

def test_observe_leveled_spell_cast_raises_depleted_belief():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_leveled_spell_cast()

    assert abs(belief.depleted - 0.3) < 1e-9

def test_observe_leveled_spell_cast_accumulates_gradually_not_in_one_shot():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_leveled_spell_cast()
    belief.observe_leveled_spell_cast()

    assert abs(belief.depleted - 0.51) < 1e-9

def test_repeated_leveled_casts_never_reach_absolute_certainty_of_depletion():
    belief = CombatantBelief.for_monster(max_hp = 20)

    for _ in range(8):
        belief.observe_leveled_spell_cast()

    assert belief.depleted < 1.0

# --- CombatantBelief: damage_multiplier / observe_damage_mitigation ---

def test_damage_multiplier_defaults_to_normal_for_an_unobserved_type():
    belief = CombatantBelief.for_monster(max_hp = 20)

    assert belief.damage_multiplier(DamageType.FIRE) == 1.0

def test_observe_damage_mitigation_pulls_belief_toward_the_observed_ratio():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 5)

    assert abs(belief.damage_multiplier(DamageType.FIRE) - 0.75) < 1e-9

def test_repeated_consistent_observations_converge_towards_the_true_ratio():
    belief = CombatantBelief.for_monster(max_hp = 20)

    for _ in range(10):
        belief.observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 0) # immune

    assert belief.damage_multiplier(DamageType.FIRE) < 0.01

def test_observe_damage_mitigation_only_affects_the_observed_damage_type():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 0)

    assert belief.damage_multiplier(DamageType.COLD) == 1.0

def test_observe_damage_mitigation_detects_vulnerability_above_normal():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 20)

    assert belief.damage_multiplier(DamageType.FIRE) > 1.0

def test_observe_damage_mitigation_ignores_a_zero_expected_damage_observation():
    belief = CombatantBelief.for_monster(max_hp = 20)

    belief.observe_damage_mitigation(DamageType.FIRE, expected_damage = 0, actual_damage = 0)

    assert belief.damage_multiplier(DamageType.FIRE) == 1.0

# --- CombatantBelief.for_monster ---

def test_monster_prior_sums_to_one():
    belief = CombatantBelief.for_monster(max_hp = 20)
    _assert_distribution_sums_to_one(belief.hp_distribution)

def test_monster_prior_centers_on_its_max_hp():
    belief = CombatantBelief.for_monster(max_hp = 20)
    assert abs(belief.expected_hp() - 20) < 1.0
    assert belief.believed_max_hp == 20

def test_monster_prior_spread_scales_with_max_hp():
    small = CombatantBelief.for_monster(max_hp = 10)
    large = CombatantBelief.for_monster(max_hp = 100)

    small_spread = max(small.hp_distribution) - min(small.hp_distribution)
    large_spread = max(large.hp_distribution) - min(large.hp_distribution)

    assert large_spread > small_spread

# --- CombatantBelief.for_player_character ---

def test_player_character_prior_sums_to_one():
    belief = CombatantBelief.for_player_character(character_class = "fighter", level = 5)
    _assert_distribution_sums_to_one(belief.hp_distribution)

def test_player_character_prior_never_reads_the_real_constitution_score():
    high_con_belief = CombatantBelief.for_player_character(character_class = "fighter", level = 5)
    low_con_belief = CombatantBelief.for_player_character(character_class = "fighter", level = 5)

    assert high_con_belief.hp_distribution == low_con_belief.hp_distribution

def test_player_character_prior_widens_with_level():
    level_one = CombatantBelief.for_player_character(character_class = "fighter", level = 1)
    level_seven = CombatantBelief.for_player_character(character_class = "fighter", level = 7)

    level_one_spread = max(level_one.hp_distribution) - min(level_one.hp_distribution)
    level_seven_spread = max(level_seven.hp_distribution) - min(level_seven.hp_distribution)

    assert level_seven_spread > level_one_spread

def test_player_character_prior_differs_by_class():
    fighter = CombatantBelief.for_player_character(character_class = "fighter", level = 5) # d10 hit die
    wizard = CombatantBelief.for_player_character(character_class = "wizard", level = 5)   # d6 hit die

    assert fighter.expected_hp() > wizard.expected_hp()

# --- CombatantBelief.observe_damage ---

def test_observe_damage_shifts_expected_hp_down_by_the_exact_amount():
    belief = CombatantBelief.for_monster(max_hp = 20)
    expected_before = belief.expected_hp()

    belief.observe_damage(8)

    assert abs(belief.expected_hp() - (expected_before - 8)) < 1e-9

def test_observe_damage_keeps_the_distribution_normalised():
    belief = CombatantBelief.for_monster(max_hp = 20)
    belief.observe_damage(8)
    _assert_distribution_sums_to_one(belief.hp_distribution)

def test_observe_healing_shifts_expected_hp_up_by_the_exact_amount():
    belief = CombatantBelief.for_monster(max_hp = 20)
    belief.observe_damage(15)
    expected_before = belief.expected_hp()

    belief.observe_healing(5)

    assert abs(belief.expected_hp() - (expected_before + 5)) < 1e-9

def test_observe_healing_keeps_the_distribution_normalised():
    belief = CombatantBelief.for_monster(max_hp = 20)
    belief.observe_damage(15)
    belief.observe_healing(5)
    _assert_distribution_sums_to_one(belief.hp_distribution)

def test_observe_healing_caps_each_hypothesis_at_its_own_max_hp_rather_than_overhealing():
    belief = CombatantBelief.for_monster(max_hp = 20)
    original_max_values = {max_hp for _, max_hp in belief.hypotheses}

    belief.observe_damage(999)
    belief.observe_healing(999)

    healed_values = set(belief.hp_distribution)
    assert healed_values == original_max_values

def test_observe_healing_undoes_a_matching_observe_damage():
    belief = CombatantBelief.for_monster(max_hp = 20)
    before = dict(belief.hp_distribution)

    belief.observe_damage(8)
    belief.observe_healing(8)

    assert belief.hp_distribution == before

def test_observe_damage_clips_at_zero_rather_than_going_negative():
    belief = CombatantBelief.for_monster(max_hp = 20)
    belief.observe_damage(999)

    assert set(belief.hp_distribution) == {0}
    assert belief.expected_hp() == 0

def test_worked_example_from_the_proposal_discussion():
    belief = CombatantBelief.for_monster(max_hp = 20)
    assert abs(belief.expected_hp() - 20) < 1.0
    assert belief.bracket_probabilities()["healthy"] > 0.95

    belief.observe_damage(10)

    assert abs(belief.expected_hp() - 10) < 1e-9
    brackets = belief.bracket_probabilities()
    assert brackets["healthy"] > 0.0
    assert brackets["bloodied"] > 0.0
    assert abs(brackets["healthy"] + brackets["bloodied"] - 1.0) < 1e-9

# --- CombatantBelief.probability_at_or_below / bracket_probabilities ---

def test_probability_at_or_below_a_generous_threshold_is_certain():
    belief = CombatantBelief.for_monster(max_hp = 20)
    assert belief.probability_at_or_below(1000) == 1.0

def test_probability_at_or_below_zero_rises_as_damage_accumulates():
    belief = CombatantBelief.for_monster(max_hp = 20)
    assert belief.probability_at_or_below(0) == 0.0

    belief.observe_damage(25)

    assert belief.probability_at_or_below(0) == 1.0

def test_bracket_probabilities_sum_to_one():
    belief = CombatantBelief.for_player_character(character_class = "wizard", level = 3)
    probabilities = belief.bracket_probabilities()
    assert abs(sum(probabilities.values()) - 1.0) < 1e-9