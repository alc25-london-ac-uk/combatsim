from enums import TargetType, TargetPriority
from policy_greedyutility import GreedyUtilityPolicy
from ai_profile import CreatureAIProfile

# --- best_attack: weapon-slot filtering (main action vs bonus/off-hand) ---

def test_best_attack_considers_ranged_weapons_for_the_main_action(make_player, make_monster, ranged_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [ranged_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = GreedyUtilityPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action is not None
    assert action.weapon is attacker.weapons[0]

def test_best_attack_never_offers_a_ranged_weapon_as_a_bonus_action(make_player, make_monster, ranged_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [ranged_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = GreedyUtilityPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = True)

    assert action is None

def test_best_attack_offers_an_off_hand_weapon_only_as_a_bonus_action(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon(name = "Off-hand Dagger", is_off_hand = True)]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = GreedyUtilityPolicy()

    main_score, main_action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)
    bonus_score, bonus_action = policy.best_attack(attacker, combat_state, {}, bonus_action = True)

    assert main_action is None
    assert bonus_action is not None

# --- best_spell: target_type-based ally/enemy filtering ---

def test_best_spell_only_offers_enemy_targeted_spells_against_enemies(make_player, make_monster, make_combat_state):
    from spell import Spell
    from enums import Ability

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
    policy = GreedyUtilityPolicy()

    score, action = policy.best_spell(caster, combat_state, {}, bonus_action = False)

    assert action is not None
    assert action.target is enemy

def test_best_spell_only_offers_ally_targeted_spells_against_allies(make_player, make_monster, make_combat_state):
    from spell import Spell
    from enums import Ability

    caster = make_player()
    caster.hp = 5 # so a healing spell actually scores well
    caster.spell_slots = {1: 1}
    heal_spell = Spell(
        name = "Test Heal Spell", level = 1, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    caster.spells = [heal_spell]

    enemy = make_monster()
    combat_state = make_combat_state(caster, enemy)
    policy = GreedyUtilityPolicy()

    score, action = policy.best_spell(caster, combat_state, {}, bonus_action = False)

    assert action is not None
    assert action.target.team == caster.team

# --- target_priority: CreatureAIProfile-configured attack target selection ---

def test_nearest_priority_prefers_the_closer_of_two_identical_enemies(make_monster, melee_weapon, make_combat_state):
    attacker = make_monster(ac = 10)
    attacker.ai.profile = CreatureAIProfile(target_priority = TargetPriority.NEAREST)
    attacker.weapons = [melee_weapon(reach = 999)]
    near = make_monster(name = "Near", ac = 10)
    far = make_monster(name = "Far", ac = 10)
    near.team = far.team = "party" # enemies of the attacker
    combat_state = make_combat_state(attacker, near, far)
    combat_state.grid.place(near, 1, 0)
    combat_state.grid.place(far, 9, 0)
    policy = GreedyUtilityPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action.target is near

def test_weakest_priority_prefers_the_lower_hp_of_two_identical_enemies(make_monster, melee_weapon, make_combat_state):
    attacker = make_monster(ac = 10)
    attacker.ai.profile = CreatureAIProfile(target_priority = TargetPriority.WEAKEST)
    attacker.weapons = [melee_weapon(reach = 999)]
    weak = make_monster(name = "Weak", ac = 10, max_hp = 20)
    weak.hp = 5
    tough = make_monster(name = "Tough", ac = 10, max_hp = 20)
    tough.hp = 20
    weak.team = tough.team = "party"
    combat_state = make_combat_state(attacker, weak, tough)
    policy = GreedyUtilityPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action.target is weak

def test_highest_threat_priority_is_a_no_op_under_the_greedy_policy(make_monster, melee_weapon, make_combat_state):
    attacker = make_monster(ac = 10)
    attacker.ai.profile = CreatureAIProfile(target_priority = TargetPriority.HIGHEST_THREAT)
    attacker.weapons = [melee_weapon(reach = 999)]
    first = make_monster(name = "First", ac = 10)
    second = make_monster(name = "Second", ac = 10)
    first.team = second.team = "party"
    combat_state = make_combat_state(attacker, first, second)
    policy = GreedyUtilityPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action.target is first

def test_target_priority_does_not_apply_to_player_characters(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon(reach = 999)]
    near = make_monster(name = "Near")
    far = make_monster(name = "Far")
    combat_state = make_combat_state(attacker, near, far)
    combat_state.grid.place(near, 1, 0)
    combat_state.grid.place(far, 9, 0)
    policy = GreedyUtilityPolicy()

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
    policy = GreedyUtilityPolicy()
    spell = _scoring_spell(level = 1)

    low_score = policy.score_spell_hit(low, target, spell, combat_state, {})
    high_score = policy.score_spell_hit(high, target, spell, combat_state, {})

    assert low_score == high_score
    assert low_score >= 7 # 2d6 averages 7; never zero dice

def test_cantrip_scoring_gains_a_die_only_from_caster_level_5(make_monster, make_combat_state):
    low = make_monster(name = "Low", spellcaster_level = 4, max_hp = 1000)
    high = make_monster(name = "High", spellcaster_level = 5, max_hp = 1000)
    target = make_monster(name = "Target", max_hp = 1000, team = "party")
    combat_state = make_combat_state(low, high, target)
    policy = GreedyUtilityPolicy()
    spell = _scoring_spell(level = 0)

    low_score = policy.score_spell_hit(low, target, spell, combat_state, {})
    high_score = policy.score_spell_hit(high, target, spell, combat_state, {})

    assert 3.4 < high_score - low_score < 3.6 # one extra d6 averages 3.5


# --- assumed AC and save modifiers (no peeking at target defences) ---

def test_score_attack_ignores_the_targets_actual_armour_class(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon()
    soft = make_monster(name = "Soft", ac = 5)
    armoured = make_monster(name = "Armoured", ac = 25)
    combat_state = make_combat_state(attacker, soft, armoured)
    policy = GreedyUtilityPolicy()

    assert policy.score_attack(attacker, soft, weapon, combat_state, {}) == policy.score_attack(attacker, armoured, weapon, combat_state, {})

def test_score_spell_hit_ignores_the_targets_actual_save_modifier_and_armour_class(make_player, make_monster, make_combat_state):
    from spell import Spell
    from enums import Ability
    from combatant import AbilityScores

    caster = make_player()
    spell = Spell(
        name = "Save Spell", level = 0, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 2, damage_sides = 6, range = 60, requires_attack_roll = True,
        save_allowed = True, save_attribute = Ability.DEXTERITY, damage_pct_on_save = 0.5
    )
    quick = make_monster(name = "Quick", ac = 5, ability_scores = AbilityScores(dexterity = 20))
    clumsy = make_monster(name = "Clumsy", ac = 25, ability_scores = AbilityScores(dexterity = 1))
    combat_state = make_combat_state(caster, quick, clumsy)
    policy = GreedyUtilityPolicy()

    assert policy.score_spell_hit(caster, quick, spell, combat_state, {}) == policy.score_spell_hit(caster, clumsy, spell, combat_state, {})


# --- fixed guesses: Greedy never updates and never peeks at an opponent's true state ---

def test_greedy_scores_identically_whatever_has_been_observed_about_the_target(make_player, make_monster, melee_weapon, make_combat_state):
    from belief import CombatantBelief

    attacker = make_player()
    weapon = melee_weapon()
    target = make_monster(max_hp = 100)
    combat_state = make_combat_state(attacker, target)
    policy = GreedyUtilityPolicy()

    untouched = {target: CombatantBelief.initial_prior_for(target)}
    wounded = {target: CombatantBelief.initial_prior_for(target)}
    wounded[target].observe_damage(95)
    wounded[target].observe_attack_roll(attack_bonus = 5, hit = False)

    assert policy.score_attack(attacker, target, weapon, combat_state, untouched) == policy.score_attack(attacker, target, weapon, combat_state, wounded)

def test_greedy_scoring_ignores_the_targets_true_hit_points(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    weapon = melee_weapon()
    healthy = make_monster(name = "Healthy", max_hp = 40)
    dying = make_monster(name = "Dying", max_hp = 40)
    dying.hp = 1
    combat_state = make_combat_state(attacker, healthy, dying)
    policy = GreedyUtilityPolicy()

    assert policy.score_attack(attacker, healthy, weapon, combat_state, {}) == policy.score_attack(attacker, dying, weapon, combat_state, {})

def test_greedy_assumes_the_class_typical_armour_class_for_player_characters(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_monster(name = "Attacker", attack_bonus = 5)
    wizard = make_player(name = "Wizard", character_class = "wizard", ac = 25)
    fighter = make_player(name = "Fighter", character_class = "fighter", ac = 5)
    weapon = melee_weapon()
    combat_state = make_combat_state(attacker, wizard, fighter)
    policy = GreedyUtilityPolicy()

    # the guess comes from the class prior (wizards are assumed squishier), not from the true AC
    assert policy.score_attack(attacker, wizard, weapon, combat_state, {}) > policy.score_attack(attacker, fighter, weapon, combat_state, {})

def test_greedy_still_knows_the_true_state_of_its_allies(make_player, make_combat_state):
    from spell import Spell
    from enums import Ability

    healer = make_player(name = "Healer")
    wounded_ally = make_player(name = "Wounded Ally")
    wounded_ally.hp = 1
    healthy_ally = make_player(name = "Healthy Ally")
    heal = Spell(
        name = "Test Heal", level = 0, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    combat_state = make_combat_state(healer, wounded_ally, healthy_ally)
    policy = GreedyUtilityPolicy()

    assert policy.score_spell_hit(healer, wounded_ally, heal, combat_state, {}) > policy.score_spell_hit(healer, healthy_ally, heal, combat_state, {})
