from enums import ActionType
from effects import Paralysed
from ai_profile import CreatureAIProfile

# --- CombatantAI: profile assignment ---

def test_combatant_ai_gives_monsters_a_creature_ai_profile(make_monster):
    monster = make_monster()

    assert isinstance(monster.ai.profile, CreatureAIProfile)

def test_combatant_ai_gives_players_no_profile(make_player):
    player = make_player()

    assert player.ai.profile is None

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
