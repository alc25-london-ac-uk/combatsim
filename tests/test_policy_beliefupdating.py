from enums import TargetType, Ability, DamageType, TargetPriority, Horizon
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

# --- Horizon.ONE integration (shared _horizon_penalty base logic covered in test_policy_greedyutility.py) ---

def test_horizon_one_makes_a_melee_attack_score_lower_than_an_otherwise_identical_ranged_one(make_player, make_monster, melee_weapon, ranged_weapon, make_combat_state):
    attacker = make_player()
    attacker.ai.profile.tactical_horizon = Horizon.ONE
    target = make_monster(ac = 10)
    target.hp = target.max_hp
    threatening_enemy = make_monster(name = "Threat", ac = 10)
    threatening_enemy.weapons = [melee_weapon(damage_dice = 4, damage_sides = 10)]
    combat_state = make_combat_state(attacker, target, threatening_enemy)
    policy = BeliefUpdatingPolicy()
    beliefs = {}

    melee_score = policy.score_attack(attacker, target, melee_weapon(reach = 999), combat_state, beliefs)
    ranged_score = policy.score_attack(attacker, target, ranged_weapon(optimal_distance = 999, maximum_distance = 999), combat_state, beliefs)

    assert ranged_score > melee_score

def test_horizon_none_does_not_penalise_melee_attacks(make_player, make_monster, melee_weapon, ranged_weapon, make_combat_state):
    attacker = make_player() # default tactical_horizon is NONE
    target = make_monster(ac = 10)
    target.hp = target.max_hp
    combat_state = make_combat_state(attacker, target)
    combat_state.grid.place(target, 9, 0) # keep the target itself out of melee range too
    policy = BeliefUpdatingPolicy()

    melee_score = policy.score_attack(attacker, target, melee_weapon(reach = 999), combat_state, {})
    ranged_score = policy.score_attack(attacker, target, ranged_weapon(optimal_distance = 999, maximum_distance = 999), combat_state, {})

    assert abs(melee_score - ranged_score) < 1e-9

def test_best_spell_offers_a_cantrip_regardless_of_spell_slots(make_player, make_monster, make_combat_state):
    from spell import Spell
    from enums import Ability

    caster = make_player()
    caster.spell_slots = {}
    caster.spells = [Spell(
        name = "Test Cantrip", level = 0, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )]
    target = make_monster()
    combat_state = make_combat_state(caster, target)
    policy = BeliefUpdatingPolicy()

    score, action = policy.best_spell(caster, combat_state, {}, bonus_action = False)

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
