from enums import ActionType, TargetType, Ability
from spell import Spell
from policy_random import RandomPolicy

# --- best_attack: random selection among legal targets/weapons ---

def test_best_attack_only_offers_enemy_targets(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon()]
    ally = make_player(name = "Ally")
    enemy = make_monster()
    combat_state = make_combat_state(attacker, ally, enemy)
    policy = RandomPolicy()

    for _ in range(20):
        score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)
        assert action.target is enemy

def test_best_attack_respects_the_bonus_action_off_hand_filter(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    off_hand = melee_weapon(name = "Off-hand Dagger", is_off_hand = True)
    attacker.weapons = [off_hand]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = RandomPolicy()

    main_score, main_action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)
    bonus_score, bonus_action = policy.best_attack(attacker, combat_state, {}, bonus_action = True)

    assert main_action is None
    assert bonus_action is not None

def test_best_attack_returns_none_when_there_are_no_valid_targets(make_player, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon()]
    combat_state = make_combat_state(attacker)
    policy = RandomPolicy()

    score, action = policy.best_attack(attacker, combat_state, {}, bonus_action = False)

    assert action is None

def test_best_attack_eventually_picks_more_than_one_of_several_valid_targets(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon()]
    enemy_a = make_monster(name = "A")
    enemy_b = make_monster(name = "B")
    combat_state = make_combat_state(attacker, enemy_a, enemy_b)
    policy = RandomPolicy()

    chosen_targets = {policy.best_attack(attacker, combat_state, {}, bonus_action = False)[1].target for _ in range(50)}

    assert chosen_targets == {enemy_a, enemy_b}

# --- best_spell: random selection among legal spells, respects slot availability ---

def _offensive_spell(**overrides):
    defaults = dict(
        name = "Test Attack Spell", level = 1, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 1, damage_sides = 6, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    defaults.update(overrides)
    return Spell(**defaults)

def test_best_spell_never_offers_a_spell_with_no_remaining_slots(make_player, make_monster, make_combat_state):
    caster = make_player()
    caster.spells = [_offensive_spell()]
    caster.spell_slots = {1: 0}
    target = make_monster()
    combat_state = make_combat_state(caster, target)
    policy = RandomPolicy()

    score, action = policy.best_spell(caster, combat_state, bonus_action = False)

    assert action is None

def test_best_spell_offers_a_cantrip_regardless_of_spell_slots(make_player, make_monster, make_combat_state):
    caster = make_player()
    caster.spells = [_offensive_spell(name = "Cantrip", level = 0)]
    caster.spell_slots = {}
    target = make_monster()
    combat_state = make_combat_state(caster, target)
    policy = RandomPolicy()

    score, action = policy.best_spell(caster, combat_state, bonus_action = False)

    assert action is not None

def test_best_spell_offers_a_spell_with_slots_remaining(make_player, make_monster, make_combat_state):
    caster = make_player()
    caster.spells = [_offensive_spell()]
    caster.spell_slots = {1: 1}
    target = make_monster()
    combat_state = make_combat_state(caster, target)
    policy = RandomPolicy()

    score, action = policy.best_spell(caster, combat_state, bonus_action = False)

    assert action is not None

# --- decide(): falls back to NONE when nothing is legal ---

def test_decide_returns_none_action_when_nothing_is_legal(make_player, make_combat_state):
    attacker = make_player()
    attacker.weapons = []
    attacker.spells = []
    combat_state = make_combat_state(attacker)
    policy = RandomPolicy()

    action = policy.decide(attacker, combat_state, {}, bonus_action = False)

    assert action.action_type == ActionType.NONE

def test_decide_picks_between_attack_and_spell_candidates_over_many_turns(make_player, make_monster, melee_weapon, make_combat_state):
    caster = make_player()
    caster.weapons = [melee_weapon()]
    caster.spells = [_offensive_spell()]
    caster.spell_slots = {1: 999}
    target = make_monster()
    combat_state = make_combat_state(caster, target)
    policy = RandomPolicy()

    action_types = {policy.decide(caster, combat_state, {}, bonus_action = False).action_type for _ in range(50)}

    assert action_types == {ActionType.ATTACK, ActionType.SPELL}
