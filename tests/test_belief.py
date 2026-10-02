from belief import CombatantBelief
from enums import DamageType, TargetType

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

# --- CombatantBelief.ground_truth_for ---

def test_ground_truth_hp_is_an_exact_point_mass(make_monster):
    monster = make_monster(max_hp = 20)
    monster.hp = 13

    belief = CombatantBelief.ground_truth_for(monster)

    assert belief.hypotheses == {(13, 20): 1.0}
    assert belief.expected_hp() == 13
    assert belief.believed_max_hp == 20

def test_ground_truth_offensive_and_healer_capable_reflect_the_real_spell_list(make_player):
    from spell import Spell
    from enums import Ability

    caster = make_player()
    damage_spell = Spell(
        name = "Damage Spell", level = 1, target_type = TargetType.ENEMY, damage_type = DamageType.FIRE,
        damage_dice = 1, damage_sides = 6, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    heal_spell = Spell(
        name = "Heal Spell", level = 1, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    caster.spells = [damage_spell, heal_spell]

    belief = CombatantBelief.ground_truth_for(caster)

    assert belief.offensive_capable == 1.0
    assert belief.healer_capable == 1.0

def test_ground_truth_capability_is_zero_for_a_non_caster(make_monster):
    monster = make_monster()
    monster.spells = []

    belief = CombatantBelief.ground_truth_for(monster)

    assert belief.offensive_capable == 0.0
    assert belief.healer_capable == 0.0

def test_ground_truth_concentrating_reflects_the_real_effect(make_player):
    from effects import Concentrating, Barkskin

    caster = make_player()
    not_concentrating = CombatantBelief.ground_truth_for(caster)
    assert not_concentrating.concentrating == 0.0

    caster.add_effect(Concentrating(maintained_effect = Barkskin(), maintained_target = caster))
    concentrating = CombatantBelief.ground_truth_for(caster)

    assert concentrating.concentrating == 1.0

def test_ground_truth_depleted_is_zero_while_any_slot_remains(make_player):
    caster = make_player()
    caster.spell_slots = {1: 0, 2: 1, 3: 0}

    belief = CombatantBelief.ground_truth_for(caster)

    assert belief.depleted == 0.0

def test_ground_truth_depleted_is_one_once_every_slot_is_spent(make_player):
    caster = make_player()
    caster.spell_slots = {1: 0, 2: 0, 3: 0}

    belief = CombatantBelief.ground_truth_for(caster)

    assert belief.depleted == 1.0

def test_ground_truth_damage_multipliers_match_the_real_resistances(make_monster):
    monster = make_monster(
        damage_resistances = [DamageType.BLUDGEONING],
        damage_vulnerabilities = [DamageType.FIRE],
        damage_immunities = [DamageType.POISON]
    )

    belief = CombatantBelief.ground_truth_for(monster)

    assert belief.damage_multiplier(DamageType.BLUDGEONING) == 0.5
    assert belief.damage_multiplier(DamageType.FIRE) == 2.0
    assert belief.damage_multiplier(DamageType.POISON) == 0.0
    assert belief.damage_multiplier(DamageType.COLD) == 1.0 # untouched type stays at the default

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

# --- CombatantBelief: AC and saving-throw beliefs ---

from enums import Ability

def test_ac_prior_is_a_normalised_distribution_for_monsters_and_players(make_monster, make_player):
    for combatant in (make_monster(), make_player(character_class = "wizard")):
        belief = CombatantBelief.initial_prior_for(combatant)

        _assert_distribution_sums_to_one(belief.ac_distribution)

def test_ac_prior_expects_a_wizard_to_be_squishier_than_a_fighter(make_player):
    wizard = CombatantBelief.initial_prior_for(make_player(character_class = "wizard"))
    fighter = CombatantBelief.initial_prior_for(make_player(character_class = "fighter"))

    assert wizard.expected_armour_class() < fighter.expected_armour_class()

def test_observing_a_hit_lowers_the_expected_ac_and_a_miss_raises_it():
    base = CombatantBelief.for_monster(max_hp = 20).expected_armour_class()

    hit_belief = CombatantBelief.for_monster(max_hp = 20)
    hit_belief.observe_attack_roll(attack_bonus = 5, hit = True)
    miss_belief = CombatantBelief.for_monster(max_hp = 20)
    miss_belief.observe_attack_roll(attack_bonus = 5, hit = False)

    assert hit_belief.expected_armour_class() < base < miss_belief.expected_armour_class()
    _assert_distribution_sums_to_one(hit_belief.ac_distribution)
    _assert_distribution_sums_to_one(miss_belief.ac_distribution)

def test_ac_update_matches_a_worked_likelihood_ratio_example():
    # +5 to hit: AC 12 is beaten by rolls 8..19 (12 of 20); AC 20 only by rolls 16..19 (4 of 20) -> likelihood ratio 3
    belief = CombatantBelief(hypotheses = {(10, 10): 1.0}, ac_distribution = {12: 0.5, 20: 0.5})

    belief.observe_attack_roll(attack_bonus = 5, hit = True)

    assert abs(belief.ac_distribution[12] - 0.75) < 1e-9
    assert abs(belief.ac_distribution[20] - 0.25) < 1e-9

def test_repeated_misses_converge_towards_a_high_ac():
    belief = CombatantBelief.for_monster(max_hp = 20)
    for _ in range(6):
        belief.observe_attack_roll(attack_bonus = 4, hit = False)

    assert belief.expected_armour_class() > 17

def test_an_extreme_observation_never_collapses_the_ac_belief():
    belief = CombatantBelief.for_monster(max_hp = 20)

    for _ in range(40):
        belief.observe_attack_roll(attack_bonus = 30, hit = False) # impossible for any AC in support

    _assert_distribution_sums_to_one(belief.ac_distribution)

def test_hit_probability_under_a_point_mass_matches_the_scoring_formula():
    belief = CombatantBelief(hypotheses = {(10, 10): 1.0}, ac_distribution = {15: 1.0})

    assert abs(belief.hit_probability(attack_bonus = 5) - (21 - (15 - 5)) / 20) < 1e-9

def test_observed_save_success_raises_the_expected_save_modifier_and_failure_lowers_it():
    base = CombatantBelief.for_monster(max_hp = 20)
    base_mean = sum(m * p for m, p in base.save_modifier_distribution(Ability.WISDOM).items())

    succeeded = CombatantBelief.for_monster(max_hp = 20)
    succeeded.observe_save(Ability.WISDOM, difficulty = 14, succeeded = True)
    failed = CombatantBelief.for_monster(max_hp = 20)
    failed.observe_save(Ability.WISDOM, difficulty = 14, succeeded = False)

    succeeded_mean = sum(m * p for m, p in succeeded.save_modifier_distribution(Ability.WISDOM).items())
    failed_mean = sum(m * p for m, p in failed.save_modifier_distribution(Ability.WISDOM).items())
    assert failed_mean < base_mean < succeeded_mean

def test_a_save_observation_only_changes_the_belief_for_that_ability():
    belief = CombatantBelief.for_monster(max_hp = 20)
    before = dict(belief.save_modifier_distribution(Ability.DEXTERITY))

    belief.observe_save(Ability.WISDOM, difficulty = 14, succeeded = True)

    assert belief.save_modifier_distribution(Ability.DEXTERITY) == before

def test_save_success_probability_under_a_point_mass_matches_the_scoring_formula():
    belief = CombatantBelief(hypotheses = {(10, 10): 1.0}, save_distributions = {Ability.DEXTERITY: {3: 1.0}})

    assert abs(belief.save_success_probability(Ability.DEXTERITY, difficulty = 15) - (21 - (15 - 3)) / 20) < 1e-9

def test_ground_truth_belief_knows_the_exact_ac_and_save_modifiers(make_monster):
    from combatant import AbilityScores

    monster = make_monster(ac = 17, ability_scores = AbilityScores(dexterity = 14))

    belief = CombatantBelief.ground_truth_for(monster)

    assert belief.ac_distribution == {17: 1.0}
    assert belief.save_modifier_distribution(Ability.DEXTERITY) == {2: 1.0}

def test_save_modifier_prior_is_centred_near_zero():
    belief = CombatantBelief.for_monster(max_hp = 20)

    mean = sum(m * p for m, p in belief.save_modifier_distribution(Ability.WISDOM).items())

    assert -0.5 < mean < 0.75


# --- belief_for: defences are shared across creatures of the same type ---

from belief import belief_for

def _typed(make_monster, name, type_name, **overrides):
    monster = make_monster(name = name, **overrides)
    monster.type_name = type_name
    return monster

def test_belief_for_returns_the_same_belief_on_repeated_calls(make_monster):
    beliefs = {}
    skeleton = _typed(make_monster, "Skeleton 1", "Skeleton")

    assert belief_for(beliefs, skeleton) is belief_for(beliefs, skeleton)

def test_ac_learned_about_one_skeleton_applies_to_a_second_one_created_later(make_monster):
    beliefs = {}
    first = _typed(make_monster, "Skeleton 1", "Skeleton")
    second = _typed(make_monster, "Skeleton 2", "Skeleton")

    belief_for(beliefs, first).observe_attack_roll(attack_bonus = 5, hit = False)
    learned = belief_for(beliefs, first).expected_armour_class()

    assert abs(belief_for(beliefs, second).expected_armour_class() - learned) < 1e-9

def test_ac_learned_after_both_beliefs_exist_reaches_both(make_monster):
    beliefs = {}
    first = _typed(make_monster, "Skeleton 1", "Skeleton")
    second = _typed(make_monster, "Skeleton 2", "Skeleton")
    prior = belief_for(beliefs, first).expected_armour_class()
    belief_for(beliefs, second)

    belief_for(beliefs, second).observe_attack_roll(attack_bonus = 5, hit = False)

    assert belief_for(beliefs, first).expected_armour_class() > prior
    assert abs(belief_for(beliefs, first).expected_armour_class() - belief_for(beliefs, second).expected_armour_class()) < 1e-9

def test_a_shared_observation_is_counted_once_not_once_per_creature(make_monster):
    shared = {}
    solo = {}
    first = _typed(make_monster, "Skeleton 1", "Skeleton")
    second = _typed(make_monster, "Skeleton 2", "Skeleton")
    lone = _typed(make_monster, "Lone", "Lone")
    belief_for(shared, first)
    belief_for(shared, second)

    belief_for(shared, first).observe_attack_roll(attack_bonus = 5, hit = False)
    belief_for(solo, lone).observe_attack_roll(attack_bonus = 5, hit = False)

    assert abs(belief_for(shared, second).expected_armour_class() - belief_for(solo, lone).expected_armour_class()) < 1e-9

def test_save_and_damage_mitigation_beliefs_are_shared_between_same_type_creatures(make_monster):
    beliefs = {}
    first = _typed(make_monster, "Skeleton 1", "Skeleton")
    second = _typed(make_monster, "Skeleton 2", "Skeleton")
    belief_for(beliefs, first)
    belief_for(beliefs, second)

    belief_for(beliefs, first).observe_save(Ability.WISDOM, difficulty = 14, succeeded = True)
    belief_for(beliefs, first).observe_damage_mitigation(DamageType.BLUDGEONING, expected_damage = 10, actual_damage = 20)

    assert belief_for(beliefs, second).save_modifier_distribution(Ability.WISDOM) == belief_for(beliefs, first).save_modifier_distribution(Ability.WISDOM)
    assert belief_for(beliefs, second).damage_multiplier(DamageType.BLUDGEONING) > 1.0

def test_defences_are_not_shared_between_different_creature_types(make_monster):
    beliefs = {}
    skeleton = _typed(make_monster, "Skeleton 1", "Skeleton")
    zombie = _typed(make_monster, "Zombie 1", "Zombie")
    prior = belief_for(beliefs, zombie).expected_armour_class()

    belief_for(beliefs, skeleton).observe_attack_roll(attack_bonus = 5, hit = False)
    belief_for(beliefs, skeleton).observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 0)

    assert abs(belief_for(beliefs, zombie).expected_armour_class() - prior) < 1e-9
    assert belief_for(beliefs, zombie).damage_multiplier(DamageType.FIRE) == 1.0

def test_creatures_without_a_type_name_never_share_beliefs(make_monster):
    beliefs = {}
    first = make_monster(name = "A")
    second = make_monster(name = "B")
    prior = belief_for(beliefs, second).expected_armour_class()

    belief_for(beliefs, first).observe_attack_roll(attack_bonus = 5, hit = False)

    assert abs(belief_for(beliefs, second).expected_armour_class() - prior) < 1e-9

def test_hp_and_spellcasting_beliefs_are_not_shared_between_same_type_creatures(make_monster):
    beliefs = {}
    first = _typed(make_monster, "Skeleton 1", "Skeleton", max_hp = 30)
    second = _typed(make_monster, "Skeleton 2", "Skeleton", max_hp = 30)
    belief_for(beliefs, first)
    belief_for(beliefs, second)
    second_hp = belief_for(beliefs, second).expected_hp()

    belief_for(beliefs, first).observe_damage(12)
    belief_for(beliefs, first).observe_offensive_cast()
    belief_for(beliefs, first).observe_concentration_spell_cast()

    second_belief = belief_for(beliefs, second)
    assert abs(second_belief.expected_hp() - second_hp) < 1e-9
    assert second_belief.offensive_capable == 0.5
    assert second_belief.concentrating == 0.0
