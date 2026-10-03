from enums import TargetType, Ability, DamageType, TargetPriority
from spell import Spell
from belief import CombatantBelief
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_greedyutility import GreedyUtilityPolicy
from ai_profile import CreatureAIProfile

# --- best_attack: weapon-slot filtering (main action vs bonus/off-hand) ---

def test_best_attack_considers_ranged_weapons_for_the_main_action(make_player, make_monster, ranged_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [ranged_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action is not None
    assert action.weapon is attacker.weapons[0]

def test_best_attack_never_offers_a_ranged_weapon_as_a_bonus_action(make_player, make_monster, ranged_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [ranged_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = True)

    assert action is None

def test_best_attack_offers_an_off_hand_weapon_only_as_a_bonus_action(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon(name = "Off-hand Dagger", is_off_hand = True)]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    main_score, main_action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)
    bonus_score, bonus_action = policy.best_attack(attacker, combat_state, {}, bonus_action = True)

    assert main_action is None
    assert bonus_action is not None

# --- best_spell: target_type-based ally/enemy filtering ---

def test_best_spell_only_offers_enemy_targeted_spells_against_enemies(make_player, make_monster, make_combat_state):
    caster = make_player()
    caster.spell_slots = {1: 1}
    damage_spell = Spell(
        name = "Test Attack Spell", level = 1, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 1, damage_sides = 6, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    caster.spells = [damage_spell]

    ally = make_player(name = "Ally")
    enemy = make_monster()
    combat_state = make_combat_state(caster, ally, enemy)
    policy = BeliefUpdatingPolicy()

    score, action = policy.best_spell(caster, combat_state, {}, bonus_action = False)

    assert action is not None
    assert action.target is enemy

def test_best_spell_only_offers_ally_targeted_spells_against_allies(make_player, make_monster, make_combat_state):
    caster = make_player()
    caster.spell_slots = {1: 1}
    heal_spell = Spell(
        name = "Test Heal Spell", level = 1, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    caster.spells = [heal_spell]

    ally = make_player(name = "Ally")
    beliefs = {ally: CombatantBelief.initial_prior_for(ally)}
    beliefs[ally].observe_damage(999) # make the heal clearly worthwhile regardless of prior spread

    enemy = make_monster()
    combat_state = make_combat_state(caster, ally, enemy)
    policy = BeliefUpdatingPolicy()

    score, action = policy.best_spell(caster, combat_state, beliefs, bonus_action = False)

    assert action is not None
    assert action.target.team == caster.team

# --- score_attack: kill_bonus is a belief-derived probability, not a ground-truth ratio ---

def test_score_attack_uses_the_passed_in_belief_rather_than_ground_truth_hp(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon()
    target = make_monster(max_hp = 20)
    target.hp = 20 # ground truth: full health
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    beliefs = {target: CombatantBelief.initial_prior_for(target)}
    beliefs[target].observe_damage(19)

    believing_dead_score = policy.score_attack(attacker, target, weapon, combat_state, beliefs)
    believing_healthy_score = policy.score_attack(attacker, target, weapon, combat_state, {})

    assert believing_dead_score > believing_healthy_score

def test_greedy_and_belief_updating_policies_can_diverge_on_the_same_ground_truth(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon(damage_dice = 2, damage_sides = 6)
    attacker.weapons = [weapon]

    tough_target = make_monster(name = "Tough", max_hp = 100, ac = 5)
    tough_target.hp = 100
    weak_target = make_monster(name = "Weak", max_hp = 100, ac = 5)
    weak_target.hp = 100
    combat_state = make_combat_state(attacker, tough_target, weak_target)

    beliefs = {
        tough_target: CombatantBelief.initial_prior_for(tough_target),
        weak_target: CombatantBelief.initial_prior_for(weak_target),
    }
    beliefs[weak_target].observe_damage(95)

    greedy_score, greedy_action = GreedyUtilityPolicy().best_attack(attacker, combat_state, {}, bonus_action = False)
    belief_score, belief_action = BeliefUpdatingPolicy().best_attack(attacker, combat_state, beliefs, bonus_action = False)

    assert belief_action.target is weak_target

# --- score_attack / score_spell_hit: priority bonus from offensive/healer belief ---

def test_score_attack_favours_a_believed_healer_over_an_identical_non_caster(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon()
    believed_healer = make_monster(name = "Healer", max_hp = 20, ac = 10)
    believed_healer.hp = 20
    plain_target = make_monster(name = "Plain", max_hp = 20, ac = 10)
    plain_target.hp = 20
    combat_state = make_combat_state(attacker, believed_healer, plain_target)

    beliefs = {
        believed_healer: CombatantBelief.initial_prior_for(believed_healer),
        plain_target: CombatantBelief.initial_prior_for(plain_target),
    }
    beliefs[believed_healer].observe_healing_cast()

    policy = BeliefUpdatingPolicy()
    healer_score = policy.score_attack(attacker, believed_healer, weapon, combat_state, beliefs)
    plain_score = policy.score_attack(attacker, plain_target, weapon, combat_state, beliefs)

    assert healer_score > plain_score

def test_score_attack_priority_bonus_weighs_healer_belief_above_offensive_belief(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon()
    believed_healer = make_monster(name = "Healer", max_hp = 20, ac = 10)
    believed_healer.hp = 20
    believed_offensive = make_monster(name = "Offensive", max_hp = 20, ac = 10)
    believed_offensive.hp = 20
    combat_state = make_combat_state(attacker, believed_healer, believed_offensive)

    beliefs = {
        believed_healer: CombatantBelief.initial_prior_for(believed_healer),
        believed_offensive: CombatantBelief.initial_prior_for(believed_offensive),
    }
    beliefs[believed_healer].observe_healing_cast()
    beliefs[believed_offensive].observe_offensive_cast()

    policy = BeliefUpdatingPolicy()
    healer_score = policy.score_attack(attacker, believed_healer, weapon, combat_state, beliefs)
    offensive_score = policy.score_attack(attacker, believed_offensive, weapon, combat_state, beliefs)

    assert healer_score > offensive_score

def test_priority_bonus_does_not_apply_to_ally_targeted_spells(make_player, make_combat_state):
    caster = make_player()
    ally = make_player(name = "Ally")
    ally.hp = 5
    combat_state = make_combat_state(caster, ally)

    heal_spell = Spell(
        name = "Test Heal Spell", level = 1, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    caster.spell_slots = {1: 1}

    beliefs = {ally: CombatantBelief.initial_prior_for(ally)}
    beliefs[ally].observe_offensive_cast() # should have no bearing on healing an ally

    policy = BeliefUpdatingPolicy()
    score_with_belief = policy.score_spell_hit(caster, ally, heal_spell, combat_state, beliefs)

    fresh_beliefs = {ally: CombatantBelief.initial_prior_for(ally)}
    score_without_belief = policy.score_spell_hit(caster, ally, heal_spell, combat_state, fresh_beliefs)

    assert score_with_belief == score_without_belief

def test_score_attack_favours_a_believed_concentrating_target_over_an_identical_non_caster(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon()
    believed_concentrating = make_monster(name = "Concentrating", max_hp = 20, ac = 10)
    believed_concentrating.hp = 20
    plain_target = make_monster(name = "Plain", max_hp = 20, ac = 10)
    plain_target.hp = 20
    combat_state = make_combat_state(attacker, believed_concentrating, plain_target)

    beliefs = {
        believed_concentrating: CombatantBelief.initial_prior_for(believed_concentrating),
        plain_target: CombatantBelief.initial_prior_for(plain_target),
    }
    beliefs[believed_concentrating].observe_concentration_spell_cast()

    policy = BeliefUpdatingPolicy()
    concentrating_score = policy.score_attack(attacker, believed_concentrating, weapon, combat_state, beliefs)
    plain_score = policy.score_attack(attacker, plain_target, weapon, combat_state, beliefs)

    assert concentrating_score > plain_score

def test_concentration_priority_weight_sits_between_offensive_and_healer_weights():
    policy = BeliefUpdatingPolicy()
    healer_belief = CombatantBelief(hypotheses = {}, offensive_capable = 0.0, healer_capable = 1.0, concentrating = 0.0)
    concentrating_belief = CombatantBelief(hypotheses = {}, offensive_capable = 0.0, healer_capable = 0.0, concentrating = 1.0)
    offensive_belief = CombatantBelief(hypotheses = {}, offensive_capable = 1.0, healer_capable = 0.0, concentrating = 0.0)

    assert policy._priority_bonus(healer_belief) > policy._priority_bonus(concentrating_belief) > policy._priority_bonus(offensive_belief)

# --- _priority_bonus: depletion discounts caster-threat terms, not concentration ---

def test_depletion_discounts_offensive_and_healer_priority_bonus():
    policy = BeliefUpdatingPolicy()
    fresh = CombatantBelief(hypotheses = {}, offensive_capable = 1.0, healer_capable = 1.0, concentrating = 0.0, depleted = 0.0)
    emptied = CombatantBelief(hypotheses = {}, offensive_capable = 1.0, healer_capable = 1.0, concentrating = 0.0, depleted = 0.8)

    assert policy._priority_bonus(emptied) < policy._priority_bonus(fresh)

def test_depletion_does_not_discount_concentration_priority_bonus():
    policy = BeliefUpdatingPolicy()
    fresh = CombatantBelief(hypotheses = {}, offensive_capable = 0.0, healer_capable = 0.0, concentrating = 1.0, depleted = 0.0)
    emptied = CombatantBelief(hypotheses = {}, offensive_capable = 0.0, healer_capable = 0.0, concentrating = 1.0, depleted = 0.8)

    assert policy._priority_bonus(emptied) == policy._priority_bonus(fresh)

def test_full_depletion_eliminates_offensive_and_healer_bonus_entirely():
    policy = BeliefUpdatingPolicy()
    belief = CombatantBelief(hypotheses = {}, offensive_capable = 1.0, healer_capable = 1.0, concentrating = 0.0, depleted = 1.0)

    assert policy._priority_bonus(belief) == 0.0

def test_a_heavily_depleted_confirmed_caster_can_score_below_an_unobserved_unknown():
    policy = BeliefUpdatingPolicy()
    unknown = CombatantBelief(hypotheses = {}, offensive_capable = 0.5, healer_capable = 0.5, concentrating = 0.0, depleted = 0.0)
    confirmed_but_spent = CombatantBelief(hypotheses = {}, offensive_capable = 1.0, healer_capable = 1.0, concentrating = 0.0, depleted = 0.9)

    assert policy._priority_bonus(confirmed_but_spent) < policy._priority_bonus(unknown)

# --- score_attack / score_spell_hit: believed damage resistance/vulnerability/immunity ---

def test_score_attack_discounts_expected_damage_for_a_believed_resistant_target(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon(damage_type = DamageType.FIRE)
    target = make_monster(ac = 10)
    target.hp = target.max_hp
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    normal_beliefs = {target: CombatantBelief.initial_prior_for(target)}
    resistant_beliefs = {target: CombatantBelief.initial_prior_for(target)}
    resistant_beliefs[target].observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 0) # a prior hit that did nothing

    normal_score = policy.score_attack(attacker, target, weapon, combat_state, normal_beliefs)
    resistant_score = policy.score_attack(attacker, target, weapon, combat_state, resistant_beliefs)

    assert resistant_score < normal_score

def test_score_attack_does_not_discount_a_different_damage_type(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon(damage_type = DamageType.COLD)
    target = make_monster(ac = 10)
    target.hp = target.max_hp
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    normal_beliefs = {target: CombatantBelief.initial_prior_for(target)}
    fire_immune_beliefs = {target: CombatantBelief.initial_prior_for(target)}
    fire_immune_beliefs[target].observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 0)

    normal_score = policy.score_attack(attacker, target, weapon, combat_state, normal_beliefs)
    cold_score = policy.score_attack(attacker, target, weapon, combat_state, fire_immune_beliefs)

    assert abs(normal_score - cold_score) < 1e-9

def test_policy_stops_preferring_a_fire_attack_once_immunity_is_believed(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    fire_weapon = melee_weapon(name = "Flaming Sword", damage_type = DamageType.FIRE)
    cold_weapon = melee_weapon(name = "Frost Sword", damage_type = DamageType.COLD)
    attacker.weapons = [fire_weapon, cold_weapon]
    target = make_monster(ac = 10)
    target.hp = target.max_hp
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    beliefs = {target: CombatantBelief.initial_prior_for(target)}
    beliefs[target].observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 0)

    score, action = policy.best_attack(attacker, combat_state, beliefs, bonus_action = False)

    assert action.weapon is cold_weapon

# --- target_priority: CreatureAIProfile-configured attack target selection ---

def test_nearest_priority_prefers_the_closer_of_two_identical_enemies(make_monster, melee_weapon, make_combat_state):
    attacker = make_monster(ac = 10)
    attacker.ai.profile = CreatureAIProfile(target_priority = TargetPriority.NEAREST)
    attacker.weapons = [melee_weapon(reach = 999)]
    near = make_monster(name = "Near", ac = 10)
    far = make_monster(name = "Far", ac = 10)
    near.team = far.team = "party"
    combat_state = make_combat_state(attacker, near, far)
    combat_state.grid.place(near, 1, 0)
    combat_state.grid.place(far, 9, 0)
    policy = BeliefUpdatingPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action.target is near

def test_weakest_priority_prefers_the_believed_lower_hp_of_two_identical_enemies(make_monster, melee_weapon, make_combat_state):
    attacker = make_monster(ac = 10)
    attacker.ai.profile = CreatureAIProfile(target_priority = TargetPriority.WEAKEST)
    attacker.weapons = [melee_weapon(reach = 999)]
    weak = make_monster(name = "Weak", ac = 10, max_hp = 20)
    weak.hp = 20
    tough = make_monster(name = "Tough", ac = 10, max_hp = 20)
    tough.hp = 20
    weak.team = tough.team = "party"
    combat_state = make_combat_state(attacker, weak, tough)
    policy = BeliefUpdatingPolicy()

    beliefs = {
        weak: CombatantBelief.initial_prior_for(weak),
        tough: CombatantBelief.initial_prior_for(tough),
    }
    beliefs[weak].observe_damage(15) # believed nearly dead, even though ground truth hp is identical

    score, action = policy.best_attack(attacker, combat_state, beliefs, bonus_action = False)

    assert action.target is weak

def test_highest_threat_priority_doubles_the_belief_derived_threat_signal(make_monster, melee_weapon, make_combat_state):
    attacker = make_monster(ac = 10)
    attacker.weapons = [melee_weapon(reach = 999)]
    believed_healer = make_monster(name = "Healer", ac = 10)
    plain_target = make_monster(name = "Plain", ac = 10)
    believed_healer.team = plain_target.team = "party"
    combat_state = make_combat_state(attacker, believed_healer, plain_target)

    beliefs = {
        believed_healer: CombatantBelief.initial_prior_for(believed_healer),
        plain_target: CombatantBelief.initial_prior_for(plain_target),
    }
    beliefs[believed_healer].observe_healing_cast()
    policy = BeliefUpdatingPolicy()

    attacker.ai.profile = CreatureAIProfile(target_priority = TargetPriority.WEAKEST)
    weakest_score = policy.score_attack(attacker, believed_healer, attacker.weapons[0], combat_state, beliefs)

    attacker.ai.profile = CreatureAIProfile(target_priority = TargetPriority.HIGHEST_THREAT)
    highest_threat_score = policy.score_attack(attacker, believed_healer, attacker.weapons[0], combat_state, beliefs)

    assert highest_threat_score > weakest_score

def test_target_priority_does_not_apply_to_player_characters(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon(reach = 999)]
    near = make_monster(name = "Near")
    far = make_monster(name = "Far")
    combat_state = make_combat_state(attacker, near, far)
    combat_state.grid.place(near, 1, 0)
    combat_state.grid.place(far, 9, 0)
    policy = BeliefUpdatingPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action is not None

# --- spell scoring: expected dice ---

def _scoring_spell(level):
    from spell import Spell
    from enums import Ability
    return Spell(
        name = "Scoring Spell", level = level, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 2, damage_sides = 6, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )

def test_leveled_spell_scoring_ignores_the_cantrip_extra_die(make_monster, make_combat_state):
    low = make_monster(name = "Low", spellcaster_level = 1, max_hp = 1000)
    high = make_monster(name = "High", spellcaster_level = 9, max_hp = 1000)
    target = make_monster(name = "Target", max_hp = 1000, team = "party")
    combat_state = make_combat_state(low, high, target)
    policy = BeliefUpdatingPolicy()
    spell = _scoring_spell(level = 1)

    low_score = policy.score_spell_hit(low, target, spell, combat_state, {})
    high_score = policy.score_spell_hit(high, target, spell, combat_state, {})

    assert low_score == high_score
    assert low_score > 7 # 2d6 averages 7; kill bonus on top, never zero dice

def test_cantrip_scoring_gains_a_die_only_from_caster_level_5(make_monster, make_combat_state):
    low = make_monster(name = "Low", spellcaster_level = 4, max_hp = 1000)
    high = make_monster(name = "High", spellcaster_level = 5, max_hp = 1000)
    target = make_monster(name = "Target", max_hp = 1000, team = "party")
    combat_state = make_combat_state(low, high, target)
    policy = BeliefUpdatingPolicy()
    spell = _scoring_spell(level = 0)

    low_score = policy.score_spell_hit(low, target, spell, combat_state, {})
    high_score = policy.score_spell_hit(high, target, spell, combat_state, {})

    assert 3.4 < high_score - low_score < 3.6 # one extra d6 averages 3.5


# --- AC and save beliefs drive scoring (no peeking at the target) ---

def test_score_attack_uses_the_believed_ac_not_the_targets_true_ac(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon()
    target = make_monster(ac = 5) # truly easy to hit
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    believed_hard = {target: CombatantBelief(hypotheses = {(20, 20): 1.0}, ac_distribution = {25: 1.0})}
    believed_easy = {target: CombatantBelief(hypotheses = {(20, 20): 1.0}, ac_distribution = {5: 1.0})}

    assert policy.score_attack(attacker, target, weapon, combat_state, believed_easy) > policy.score_attack(attacker, target, weapon, combat_state, believed_hard)

def test_score_spell_hit_uses_the_believed_save_modifier_not_the_targets_true_one(make_player, make_monster, make_combat_state):
    from combatant import AbilityScores

    caster = make_player()
    target = make_monster(ability_scores = AbilityScores(dexterity = 1)) # truly terrible at dex saves
    spell = Spell(
        name = "Save Spell", level = 0, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 2, damage_sides = 6, range = 60, requires_attack_roll = False,
        save_allowed = True, save_attribute = Ability.DEXTERITY, damage_pct_on_save = 0
    )
    combat_state = make_combat_state(caster, target)
    policy = BeliefUpdatingPolicy()

    believed_strong = {target: CombatantBelief(hypotheses = {(20, 20): 1.0}, save_distributions = {Ability.DEXTERITY: {10: 1.0}})}
    believed_weak = {target: CombatantBelief(hypotheses = {(20, 20): 1.0}, save_distributions = {Ability.DEXTERITY: {-3: 1.0}})}

    assert policy.score_spell_hit(caster, target, spell, combat_state, believed_weak) > policy.score_spell_hit(caster, target, spell, combat_state, believed_strong)


# --- exploration: untried damage types are treated optimistically ---

def _two_weapon_attacker(make_player, melee_weapon):
    attacker = make_player()
    attacker.weapons = [
        melee_weapon(name = "Longsword", damage_type = DamageType.SLASHING),
        melee_weapon(name = "Warhammer", damage_type = DamageType.BLUDGEONING),
    ]
    return attacker

def _best_weapon_name(policy, attacker, target, combat_state, beliefs):
    _, action = policy.best_attack(attacker, combat_state, beliefs, bonus_action = False)
    return action.weapon.name

def test_has_tested_is_false_until_a_damage_type_has_been_observed():
    belief = CombatantBelief.for_monster(max_hp = 20)

    assert not belief.has_tested(DamageType.FIRE)
    belief.observe_damage_mitigation(DamageType.FIRE, expected_damage = 10, actual_damage = 10)
    assert belief.has_tested(DamageType.FIRE)

def test_ground_truth_beliefs_count_every_damage_type_as_known(make_monster):
    belief = CombatantBelief.ground_truth_for(make_monster())

    assert all(belief.has_tested(damage_type) for damage_type in DamageType)

def test_the_policy_tries_an_untested_damage_type_once_the_first_has_proved_ordinary(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = _two_weapon_attacker(make_player, melee_weapon)
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    beliefs = {target: CombatantBelief.for_monster(max_hp = 20)}
    beliefs[target].observe_damage_mitigation(DamageType.SLASHING, expected_damage = 10, actual_damage = 10)

    assert _best_weapon_name(BeliefUpdatingPolicy(), attacker, target, combat_state, beliefs) == "Warhammer"

def test_the_policy_sticks_with_a_damage_type_that_proved_vulnerable(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = _two_weapon_attacker(make_player, melee_weapon)
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    beliefs = {target: CombatantBelief.for_monster(max_hp = 20)}
    beliefs[target].observe_damage_mitigation(DamageType.SLASHING, expected_damage = 10, actual_damage = 10)
    for _ in range(3):
        beliefs[target].observe_damage_mitigation(DamageType.BLUDGEONING, expected_damage = 10, actual_damage = 20)

    assert _best_weapon_name(BeliefUpdatingPolicy(), attacker, target, combat_state, beliefs) == "Warhammer"

def test_the_policy_returns_to_the_first_damage_type_once_the_second_proves_resisted(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = _two_weapon_attacker(make_player, melee_weapon)
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    beliefs = {target: CombatantBelief.for_monster(max_hp = 20)}
    beliefs[target].observe_damage_mitigation(DamageType.SLASHING, expected_damage = 10, actual_damage = 10)
    beliefs[target].observe_damage_mitigation(DamageType.BLUDGEONING, expected_damage = 10, actual_damage = 5)

    assert _best_weapon_name(BeliefUpdatingPolicy(), attacker, target, combat_state, beliefs) == "Longsword"

def test_exploration_is_not_repeated_for_a_sibling_whose_type_has_already_been_tested(make_player, make_monster, melee_weapon, make_combat_state):
    from belief import belief_for

    attacker = _two_weapon_attacker(make_player, melee_weapon)
    first = make_monster(name = "Skeleton 1")
    first.type_name = "Skeleton"
    second = make_monster(name = "Skeleton 2")
    second.type_name = "Skeleton"
    combat_state = make_combat_state(attacker, first, second)
    beliefs = {}
    belief_for(beliefs, first).observe_damage_mitigation(DamageType.SLASHING, expected_damage = 10, actual_damage = 10)
    belief_for(beliefs, first).observe_damage_mitigation(DamageType.BLUDGEONING, expected_damage = 10, actual_damage = 5)
    # only the second sibling is alive to be attacked, and it inherits what was learned about the first
    first.hp = 0

    assert _best_weapon_name(BeliefUpdatingPolicy(), attacker, second, combat_state, beliefs) == "Longsword"

def test_omniscient_never_explores_because_it_already_knows_every_damage_type(make_player, make_monster, melee_weapon, make_combat_state):
    from policy_omniscient import OmniscientPolicy

    attacker = _two_weapon_attacker(make_player, melee_weapon)
    target = make_monster() # no resistances, so both weapons are equally good
    combat_state = make_combat_state(attacker, target)

    assert _best_weapon_name(OmniscientPolicy(), attacker, target, combat_state, {}) == "Longsword"

# --- allies are not hidden ---

def test_belief_updating_uses_the_true_hp_of_allies_when_scoring_healing(make_player, make_combat_state):
    healer = make_player(name = "Healer")
    wounded_ally = make_player(name = "Wounded Ally")
    wounded_ally.hp = 1
    heal = Spell(
        name = "Test Heal", level = 0, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    combat_state = make_combat_state(healer, wounded_ally)
    stale_belief = {wounded_ally: CombatantBelief(hypotheses = {(wounded_ally.max_hp, wounded_ally.max_hp): 1.0})} # believes the ally is unhurt

    score = BeliefUpdatingPolicy().score_spell_hit(healer, wounded_ally, heal, combat_state, stale_belief)

    assert score > 0


# --- scoring agrees with what the engine rolls ---

def test_expected_spell_damage_includes_the_spells_own_flat_bonus_and_nothing_else(make_monster, make_combat_state):
    from belief import CombatantBelief

    caster = make_monster(name = "Caster", spellcaster_level = 1, spell_bonus = 9)
    target = make_monster(name = "Target", max_hp = 1000, team = "party")
    combat_state = make_combat_state(caster, target)
    plain = Spell(name = "Plain", level = 1, target_type = TargetType.ENEMY, damage_type = None, damage_dice = 3, damage_sides = 4, range = 120, requires_attack_roll = False, save_allowed = False, save_attribute = Ability.DEXTERITY)
    missile = Spell(name = "Missile", level = 1, target_type = TargetType.ENEMY, damage_type = None, damage_dice = 3, damage_sides = 4, range = 120, requires_attack_roll = False, save_allowed = False, save_attribute = Ability.DEXTERITY, damage_bonus = 3)
    policy = BeliefUpdatingPolicy()
    beliefs = {target: CombatantBelief.initial_prior_for(target)}

    assert abs(policy.score_spell_hit(caster, target, missile, combat_state, beliefs) - policy.score_spell_hit(caster, target, plain, combat_state, beliefs) - 3) < 1e-9

def test_expected_damage_of_a_multi_ray_spell_scales_with_the_ray_count(make_monster, make_combat_state):
    from belief import CombatantBelief

    caster = make_monster(name = "Caster", spellcaster_level = 1, spell_bonus = 30) # hits every time
    target = make_monster(name = "Target", max_hp = 100000, team = "party")
    combat_state = make_combat_state(caster, target)
    one_ray = Spell(name = "One", level = 2, target_type = TargetType.ENEMY, damage_type = None, damage_dice = 2, damage_sides = 6, range = 120, requires_attack_roll = True, save_allowed = False, save_attribute = Ability.DEXTERITY, ray_count = 1)
    three_rays = Spell(name = "Three", level = 2, target_type = TargetType.ENEMY, damage_type = None, damage_dice = 2, damage_sides = 6, range = 120, requires_attack_roll = True, save_allowed = False, save_attribute = Ability.DEXTERITY, ray_count = 3)
    policy = BeliefUpdatingPolicy()
    no_priority = CombatantBelief.initial_prior_for(target)
    no_priority.offensive_capable = 0.0
    no_priority.healer_capable = 0.0
    beliefs = {target: no_priority}

    assert abs(policy.score_spell_hit(caster, target, three_rays, combat_state, beliefs) - 3 * policy.score_spell_hit(caster, target, one_ray, combat_state, beliefs)) < 1e-9

def test_expected_healing_uses_the_spells_own_dice(make_player, make_combat_state):
    healer = make_player(name = "Healer")
    ally = make_player(name = "Ally")
    ally.hp = 1
    combat_state = make_combat_state(healer, ally)
    small_heal = Spell(name = "Small", level = 0, target_type = TargetType.ALLY, damage_type = None, damage_dice = 1, damage_sides = 4, range = 60, requires_attack_roll = False, save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True)
    big_heal = Spell(name = "Big", level = 0, target_type = TargetType.ALLY, damage_type = None, damage_dice = 3, damage_sides = 8, range = 60, requires_attack_roll = False, save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True)
    policy = BeliefUpdatingPolicy()

    assert policy.score_spell_hit(healer, ally, big_heal, combat_state, {}) > policy.score_spell_hit(healer, ally, small_heal, combat_state, {})


# --- ally buff valuation ---

def _shield_of_faith_spell():
    from effects import ShieldOfFaith

    return Spell(
        name = "Shield of Faith", level = 1, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 0, damage_sides = 0, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, effect = ShieldOfFaith, is_bonus_action = True
    )

def test_an_ac_buff_on_an_ally_is_worth_more_when_enemies_hit_harder(make_player, make_monster, melee_weapon, make_combat_state):
    cleric = make_player(name = "Cleric")
    ally = make_player(name = "Ally")
    weak_enemy = make_monster(name = "Weak")
    weak_enemy.weapons = [melee_weapon(damage_dice = 1, damage_sides = 4)]
    strong_enemy = make_monster(name = "Strong")
    strong_enemy.weapons = [melee_weapon(damage_dice = 4, damage_sides = 10)]
    policy = BeliefUpdatingPolicy()
    spell = _shield_of_faith_spell()

    weak_value = policy.score_spell_hit(cleric, ally, spell, make_combat_state(cleric, ally, weak_enemy), {})
    strong_value = policy.score_spell_hit(cleric, ally, spell, make_combat_state(cleric, ally, strong_enemy), {})

    assert 0 < weak_value < strong_value

def test_an_ac_buff_is_worth_nothing_when_there_are_no_enemies(make_player, make_combat_state):
    cleric = make_player(name = "Cleric")
    ally = make_player(name = "Ally")

    value = BeliefUpdatingPolicy().score_spell_hit(cleric, ally, _shield_of_faith_spell(), make_combat_state(cleric, ally), {})

    assert value == 0

def test_an_ac_buff_is_not_stacked_on_an_ally_who_already_has_it(make_player, make_monster, melee_weapon, make_combat_state):
    from effects import ShieldOfFaith

    cleric = make_player(name = "Cleric")
    ally = make_player(name = "Ally")
    enemy = make_monster()
    enemy.weapons = [melee_weapon(damage_dice = 2, damage_sides = 8)]
    ally.add_effect(ShieldOfFaith())

    value = BeliefUpdatingPolicy().score_spell_hit(cleric, ally, _shield_of_faith_spell(), make_combat_state(cleric, ally, enemy), {})

    assert value < 0

def test_a_cleric_with_nothing_better_to_do_chooses_to_buff_a_threatened_ally_as_a_bonus_action(make_player, make_monster, melee_weapon, make_combat_state):
    cleric = make_player(name = "Cleric")
    cleric.spells = [_shield_of_faith_spell()]
    cleric.spell_slots = {1: 1}
    ally = make_player(name = "Ally")
    enemy = make_monster()
    enemy.weapons = [melee_weapon(damage_dice = 3, damage_sides = 10)]
    combat_state = make_combat_state(cleric, ally, enemy)

    score, action = BeliefUpdatingPolicy().best_spell(cleric, combat_state, {}, bonus_action = True)

    assert action is not None and action.spell.name == "Shield of Faith"


# --- reachable this turn: an action that cannot be made this turn is worth no damage ---

def _state_with_target_at(attacker, target, squares_away):
    from world import Grid, CombatState

    grid = Grid(30, 30)
    grid.place(attacker, 0, 0)
    grid.place(target, squares_away, 0)
    return CombatState(grid = grid, initiative_order = [attacker, target])

def test_a_melee_attack_beyond_this_turns_reach_is_worth_no_damage(make_player, make_monster, melee_weapon):
    attacker = make_player() # speed 30: can move 30 ft then hit at 5 ft reach, i.e. 35 ft away at most
    target = make_monster()
    policy = BeliefUpdatingPolicy()
    weapon = melee_weapon(reach = 5)

    reachable = policy.score_attack(attacker, target, weapon, _state_with_target_at(attacker, target, 7), {}) # 35 ft
    out_of_reach = policy.score_attack(attacker, target, weapon, _state_with_target_at(attacker, target, 8), {}) # 40 ft

    assert reachable > 1 # still carries its movement penalty, but is worth real damage
    assert -1 < out_of_reach <= 0

def test_the_reach_boundary_is_exactly_movement_plus_weapon_range(make_player, make_monster, melee_weapon):
    attacker = make_player()
    attacker.movement = 10
    target = make_monster()
    policy = BeliefUpdatingPolicy()
    weapon = melee_weapon(reach = 5)

    assert policy.score_attack(attacker, target, weapon, _state_with_target_at(attacker, target, 3), {}) > 1 # 15 ft = 10 + 5
    assert policy.score_attack(attacker, target, weapon, _state_with_target_at(attacker, target, 4), {}) <= 0 # 20 ft

def test_movement_already_spent_this_turn_shrinks_what_can_be_reached(make_player, make_monster, melee_weapon):
    attacker = make_player()
    target = make_monster()
    policy = BeliefUpdatingPolicy()
    weapon = melee_weapon(reach = 5)
    combat_state = _state_with_target_at(attacker, target, 6) # 30 ft

    fresh = policy.score_attack(attacker, target, weapon, combat_state, {})
    attacker.movement = 0
    spent = policy.score_attack(attacker, target, weapon, combat_state, {})

    assert fresh > 1 and spent <= 0

def test_a_distant_target_is_attacked_with_the_bow_rather_than_a_sword_that_cannot_reach(make_player, make_monster, melee_weapon, ranged_weapon):
    attacker = make_player()
    attacker.weapons = [melee_weapon(name = "Sword", damage_dice = 1, damage_sides = 10), ranged_weapon(name = "Bow", damage_dice = 1, damage_sides = 8)]
    target = make_monster()
    combat_state = _state_with_target_at(attacker, target, 12) # 60 ft
    policy = BeliefUpdatingPolicy()

    _, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action.weapon.name == "Bow"

def test_the_sword_is_still_preferred_when_it_can_reach_this_turn(make_player, make_monster, melee_weapon, ranged_weapon):
    attacker = make_player()
    attacker.weapons = [melee_weapon(name = "Sword", damage_dice = 1, damage_sides = 10), ranged_weapon(name = "Bow", damage_dice = 1, damage_sides = 8)]
    target = make_monster()
    combat_state = _state_with_target_at(attacker, target, 4) # 20 ft
    policy = BeliefUpdatingPolicy()

    _, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action.weapon.name == "Sword"

def test_a_combatant_with_nothing_in_reach_still_chooses_to_close_on_the_nearest_enemy(make_player, make_monster, melee_weapon):
    from world import Grid, CombatState

    attacker = make_player()
    attacker.weapons = [melee_weapon(reach = 5)]
    near = make_monster(name = "Near")
    far = make_monster(name = "Far")
    grid = Grid(30, 30)
    grid.place(attacker, 0, 0)
    grid.place(near, 10, 0) # 50 ft
    grid.place(far, 20, 0) # 100 ft
    combat_state = CombatState(grid = grid, initiative_order = [attacker, near, far])

    score, action = BeliefUpdatingPolicy().best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action is not None and action.target is near

def test_a_target_that_cannot_be_approached_is_not_chosen_even_to_close_in(make_player, make_monster, melee_weapon):
    from effects import Effect

    class Cannot(Effect):
        def forbids_approaching(self, other):
            return True

    attacker = make_player()
    attacker.weapons = [melee_weapon(reach = 5)]
    attacker.effects.append(Cannot())
    target = make_monster()
    combat_state = _state_with_target_at(attacker, target, 12)

    score, action = BeliefUpdatingPolicy().best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action is None

def test_a_spell_out_of_reach_this_turn_is_worth_no_damage(make_player, make_monster):
    caster = make_player()
    caster.spell_slots = {1: 1}
    target = make_monster()
    touch_spell = Spell(
        name = "Touch Spell", level = 1, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 3, damage_sides = 10, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    policy = BeliefUpdatingPolicy()

    in_reach = policy.score_spell(caster, target, touch_spell, _state_with_target_at(caster, target, 4), {})
    out_of_reach = policy.score_spell(caster, target, touch_spell, _state_with_target_at(caster, target, 9), {})

    assert in_reach > 10
    assert -1 < out_of_reach <= 0
