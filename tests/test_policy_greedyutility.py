from enums import TargetType
from policy_greedyutility import GreedyUtilityPolicy

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

    score, action = policy.best_spell(caster, combat_state, bonus_action = False)

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

    score, action = policy.best_spell(caster, combat_state, bonus_action = False)

    assert action is not None
    assert action.target.team == caster.team
