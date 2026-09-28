from enums import ActionType, TargetType
from effects import Paralysed

# --- best_attack: weapon-slot filtering (main action vs bonus/off-hand) ---

def test_best_attack_considers_ranged_weapons_for_the_main_action(make_player, make_monster, ranged_weapon, make_combat_state):
    # regression: an earlier version of this filter accidentally excluded
    # every RangedWeapon from ever being selected at all, not just from the
    # bonus-action slot
    attacker = make_player()
    attacker.weapons = [ranged_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)

    score, action = attacker.ai.best_attack(combat_state, bonus_action = False)

    assert action is not None
    assert action.weapon is attacker.weapons[0]

def test_best_attack_never_offers_a_ranged_weapon_as_a_bonus_action(make_player, make_monster, ranged_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [ranged_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)

    score, action = attacker.ai.best_attack(combat_state, bonus_action = True)

    assert action is None

def test_best_attack_offers_an_off_hand_weapon_only_as_a_bonus_action(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon(name = "Off-hand Dagger", is_off_hand = True)]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)

    main_score, main_action = attacker.ai.best_attack(combat_state, bonus_action = False)
    bonus_score, bonus_action = attacker.ai.best_attack(combat_state, bonus_action = True)

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

    score, action = caster.ai.best_spell(combat_state, bonus_action = False)

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

    score, action = caster.ai.best_spell(combat_state, bonus_action = False)

    assert action is not None
    assert action.target.team == caster.team

# --- take_turn(): action-economy resource consumption ---

def test_take_turn_consumes_the_main_action(make_player, make_monster, make_combat_state):
    attacker = make_player()
    target = make_monster()
    make_combat_state(attacker, target)
    combat_state = make_combat_state(attacker, target)

    attacker.ai.take_turn(combat_state)

    assert attacker.has_action is False

def test_take_turn_consumes_the_bonus_action_even_with_nothing_to_do(make_player, make_monster, make_combat_state):
    attacker = make_player() # no bonus-action spells available
    target = make_monster()
    combat_state = make_combat_state(attacker, target)

    attacker.ai.take_turn(combat_state)

    assert attacker.has_bonus_action is False

def test_paralysed_combatant_skips_its_entire_turn(make_player, make_monster, make_combat_state):
    attacker = make_player()
    attacker.add_effect(Paralysed())
    target = make_monster()
    combat_state = make_combat_state(attacker, target)

    results = attacker.ai.take_turn(combat_state)

    assert len(results) == 1
    assert results[0].action_type == ActionType.NONE
    assert results[0].rationale == "Paralysed"

# --- execute(): bonus-action attacks don't get Extra Attack's multiplier ---

def test_bonus_action_attack_is_capped_at_one_swing_even_with_extra_attack(make_player, make_monster, melee_weapon, make_combat_state):
    # regression: Extra Attack only applies to the Attack action, never to a bonus-action (off-hand) attack, regardless of attack_count
    attacker = make_player(character_class = "fighter", level = 5) # attack_count == 2
    assert attacker.attack_count == 2

    off_hand = melee_weapon(name = "Off-hand Dagger", is_off_hand = True)
    attacker.weapons = [melee_weapon(name = "Main Hand Sword"), off_hand]
    target = make_monster()
    target.hp = 9999 # stays alive through every swing so nothing retargets
    combat_state = make_combat_state(attacker, target)

    from actions import Action
    bonus_action = Action(ActionType.ATTACK, target, weapon = off_hand)
    results = attacker.ai.execute(bonus_action, combat_state, bonus_action = True)

    attack_results = [r for r in results if r.action_type == ActionType.ATTACK]
    assert len(attack_results) == 1

def test_main_action_attack_uses_the_full_attack_count(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player(character_class = "fighter", level = 5) # attack_count == 2
    weapon = melee_weapon(name = "Main Hand Sword")
    attacker.weapons = [weapon]
    target = make_monster()
    target.hp = 9999
    combat_state = make_combat_state(attacker, target)

    from actions import Action
    main_action = Action(ActionType.ATTACK, target, weapon = weapon)
    results = attacker.ai.execute(main_action, combat_state, bonus_action = False)

    attack_results = [r for r in results if r.action_type == ActionType.ATTACK]
    assert len(attack_results) == 2
