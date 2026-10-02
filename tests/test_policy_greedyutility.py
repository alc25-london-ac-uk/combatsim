from enums import TargetType, TargetPriority, Horizon
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

# --- _horizon_penalty (Policy base class, shared by all policies) ---

def test_horizon_penalty_is_zero_at_the_default_horizon_none(make_player, make_monster, melee_weapon, make_combat_state):
    combatant = make_player()
    enemy = make_monster()
    enemy.weapons = [melee_weapon()]
    combat_state = make_combat_state(combatant, enemy)
    policy = GreedyUtilityPolicy()

    assert combatant.ai.profile.tactical_horizon == Horizon.NONE
    assert policy._horizon_penalty(combatant, combat_state, exposed_to_melee = True) == 0.0

def test_horizon_penalty_is_zero_when_not_exposed_to_melee(make_player, make_monster, melee_weapon, make_combat_state):
    combatant = make_player()
    combatant.ai.profile.tactical_horizon = Horizon.ONE
    enemy = make_monster()
    enemy.weapons = [melee_weapon()]
    combat_state = make_combat_state(combatant, enemy)
    policy = GreedyUtilityPolicy()

    assert policy._horizon_penalty(combatant, combat_state, exposed_to_melee = False) == 0.0

def test_horizon_penalty_is_zero_at_horizon_multi(make_player, make_monster, melee_weapon, make_combat_state):
    combatant = make_player()
    combatant.ai.profile.tactical_horizon = Horizon.MULTI
    enemy = make_monster()
    enemy.weapons = [melee_weapon()]
    combat_state = make_combat_state(combatant, enemy)
    policy = GreedyUtilityPolicy()

    assert policy._horizon_penalty(combatant, combat_state, exposed_to_melee = True) == 0.0

def test_horizon_penalty_is_negative_when_exposed_at_horizon_one(make_player, make_monster, melee_weapon, make_combat_state):
    combatant = make_player()
    combatant.ai.profile.tactical_horizon = Horizon.ONE
    enemy = make_monster()
    enemy.weapons = [melee_weapon()]
    combat_state = make_combat_state(combatant, enemy)
    policy = GreedyUtilityPolicy()

    assert policy._horizon_penalty(combatant, combat_state, exposed_to_melee = True) < 0.0

def test_horizon_penalty_picks_the_worst_of_several_enemies(make_player, make_monster, melee_weapon, make_combat_state):
    combatant = make_player()
    combatant.ai.profile.tactical_horizon = Horizon.ONE
    weak_enemy = make_monster(name = "Weak")
    weak_enemy.weapons = [melee_weapon(damage_dice = 1, damage_sides = 4)]
    strong_enemy = make_monster(name = "Strong")
    strong_enemy.weapons = [melee_weapon(damage_dice = 4, damage_sides = 10)]
    combat_state = make_combat_state(combatant, weak_enemy, strong_enemy)
    policy = GreedyUtilityPolicy()

    penalty_with_both = policy._horizon_penalty(combatant, combat_state, exposed_to_melee = True)

    weak_only_state = make_combat_state(combatant, weak_enemy)
    penalty_weak_only = policy._horizon_penalty(combatant, weak_only_state, exposed_to_melee = True)

    assert penalty_with_both < penalty_weak_only

def test_horizon_penalty_ignores_dead_and_allied_combatants(make_player, make_monster, melee_weapon, make_combat_state):
    combatant = make_player()
    combatant.ai.profile.tactical_horizon = Horizon.ONE
    dead_enemy = make_monster(name = "Dead")
    dead_enemy.weapons = [melee_weapon(damage_dice = 10, damage_sides = 10)]
    dead_enemy.hp = 0
    ally = make_player(name = "Ally")
    ally.weapons = [melee_weapon(damage_dice = 10, damage_sides = 10)]
    combat_state = make_combat_state(combatant, dead_enemy, ally)
    policy = GreedyUtilityPolicy()

    assert policy._horizon_penalty(combatant, combat_state, exposed_to_melee = True) == 0.0

# --- Horizon.ONE integration: score_attack / score_spell ---

def test_horizon_one_makes_a_melee_attack_score_lower_than_an_otherwise_identical_ranged_one(make_player, make_monster, melee_weapon, ranged_weapon, make_combat_state):
    attacker = make_player()
    attacker.ai.profile.tactical_horizon = Horizon.ONE
    target = make_monster(ac = 10)
    threatening_enemy = make_monster(name = "Threat", ac = 10)
    threatening_enemy.weapons = [melee_weapon(damage_dice = 4, damage_sides = 10)]
    combat_state = make_combat_state(attacker, target, threatening_enemy)
    policy = GreedyUtilityPolicy()

    melee_score = policy.score_attack(attacker, target, melee_weapon(reach = 999), combat_state, {})
    ranged_score = policy.score_attack(attacker, target, ranged_weapon(optimal_distance = 999, maximum_distance = 999), combat_state, {})

    assert ranged_score > melee_score

def test_horizon_one_penalises_a_melee_range_spell(make_player, make_monster, make_combat_state):
    from spell import Spell
    from enums import Ability

    caster = make_player()
    caster.ai.profile.tactical_horizon = Horizon.ONE
    caster.spell_slots = {1: 1}
    target = make_monster(ac = 10)
    threatening_enemy = make_monster(name = "Threat", ac = 10)
    from weapon import MeleeWeapon
    from enums import DamageType
    threatening_enemy.weapons = [MeleeWeapon(name = "Claws", damage_dice = 4, damage_sides = 10, damage_type = DamageType.SLASHING, reach = 5, finesse = False)]
    combat_state = make_combat_state(caster, target, threatening_enemy)

    melee_spell = Spell(
        name = "Melee Spell", level = 1, target_type = TargetType.ENEMY, damage_type = DamageType.FORCE,
        damage_dice = 2, damage_sides = 6, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    ranged_spell = Spell(
        name = "Ranged Spell", level = 1, target_type = TargetType.ENEMY, damage_type = DamageType.FORCE,
        damage_dice = 2, damage_sides = 6, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    policy = GreedyUtilityPolicy()

    melee_score = policy.score_spell(caster, target, melee_spell, combat_state, {})
    caster.spell_slots = {1: 1} # score_spell doesn't mutate slots, but keep state obviously fresh
    ranged_score = policy.score_spell(caster, target, ranged_spell, combat_state, {})

    assert ranged_score > melee_score

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
    policy = GreedyUtilityPolicy()

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
    policy = GreedyUtilityPolicy()
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
    policy = GreedyUtilityPolicy()
    spell = _scoring_spell(level = 0)

    low_score = policy.score_spell_hit(low, target, spell, combat_state, {})
    high_score = policy.score_spell_hit(high, target, spell, combat_state, {})

    assert 3.4 < high_score - low_score < 3.6 # one extra d6 averages 3.5

# --- point-estimate HP (no peeking at true HP) ---

def test_score_attack_uses_estimated_hp_not_the_targets_true_hp(make_player, make_monster, melee_weapon, make_combat_state):
    from belief import CombatantBelief

    attacker = make_player()
    weapon = melee_weapon()
    target = make_monster(max_hp = 100)
    target.hp = 1 # truly almost dead
    combat_state = make_combat_state(attacker, target)
    policy = GreedyUtilityPolicy()

    believed_healthy = {target: CombatantBelief(hypotheses = {(100, 100): 1.0})}
    believed_dying = {target: CombatantBelief(hypotheses = {(1, 100): 1.0})}

    healthy_score = policy.score_attack(attacker, target, weapon, combat_state, believed_healthy)
    dying_score = policy.score_attack(attacker, target, weapon, combat_state, believed_dying)

    assert dying_score > healthy_score # the belief drives the kill bonus, not target.hp

def test_weakest_priority_follows_the_estimated_hp_fraction(make_player, make_monster, make_combat_state):
    from belief import CombatantBelief

    attacker = make_monster(name = "Attacker")
    attacker.ai = type("AI", (), {"profile": CreatureAIProfile(target_priority = TargetPriority.WEAKEST)})()
    target = make_player()
    combat_state = make_combat_state(attacker, target)
    policy = GreedyUtilityPolicy()

    hurt = {target: CombatantBelief(hypotheses = {(10, 100): 1.0})}
    fresh = {target: CombatantBelief(hypotheses = {(100, 100): 1.0})}

    assert policy._target_priority_bonus(attacker, target, 5, hurt) > policy._target_priority_bonus(attacker, target, 5, fresh)

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
