import combat
from combat import format_attack_result, format_spell_result, log_action, run_combat, monte_carlo
from actions import ActionResult
from enums import ActionType, AttackResult

# --- format_attack_result / format_spell_result: actor attribution ---

def test_format_attack_result_uses_the_actor_field_not_the_turn_holder(make_player):
    # e.g. an opportunity attack: it happens during the mover's turn, but was actually performed by a different combatant reacting to it
    turn_holder = make_player(name = "TurnHolder")
    target = make_player(name = "Target")
    result = ActionResult(
        action_type = ActionType.ATTACK, target = target, actor = "RealAttacker",
        weapon = "Sword", amount = 5, attack_result = AttackResult.HIT, target_hp_after_action = 10
    )

    text = format_attack_result(turn_holder, result)

    assert text.startswith("RealAttacker attacks Target")
    assert "TurnHolder" not in text

def test_format_attack_result_reports_a_miss(make_player):
    turn_holder = make_player()
    target = make_player(name = "Target")
    result = ActionResult(action_type = ActionType.ATTACK, target = target, actor = "Attacker", weapon = "Sword", attack_result = AttackResult.MISS)

    text = format_attack_result(turn_holder, result)

    assert text.endswith("miss.")

def test_format_spell_result_uses_the_actor_field_not_the_turn_holder(make_player):
    turn_holder = make_player(name = "TurnHolder")
    target = make_player(name = "Target")
    result = ActionResult(
        action_type = ActionType.SPELL, target = target, actor = "RealCaster", spell = "Fireball",
        amount = 10, attack_result = AttackResult.HIT, target_hp_after_action = 5
    )

    text = format_spell_result(turn_holder, result)

    assert text.startswith("RealCaster casts")
    assert "TurnHolder" not in text

def test_format_spell_result_reports_healing(make_player):
    turn_holder = make_player()
    target = make_player(name = "Target")
    result = ActionResult(action_type = ActionType.SPELL, target = target, actor = "Healer", spell = "Cure Wounds", amount = 7, is_healing = True, target_hp_after_action = 20)

    text = format_spell_result(turn_holder, result)

    assert "heals 7" in text

def test_log_action_reports_none_action_as_skipped(make_player):
    turn_holder = make_player(name = "Idle")
    result = ActionResult(action_type = ActionType.NONE, target = turn_holder)

    lines = log_action(turn_holder, [result])

    assert lines == ["Idle skipped their turn."]

# --- run_combat: win/draw conditions ---

def test_run_combat_returns_party_when_all_enemies_are_defeated(monkeypatch, make_player, make_monster, melee_weapon):
    monkeypatch.setattr("random.randint", lambda a, b: 15)
    attacker = make_player()
    attacker.weapons = [melee_weapon()]
    enemy = make_monster(ac = 1, max_hp = 1)
    enemy.weapons = [] # cannot fight back

    winner = run_combat([attacker], [enemy], log = False)

    assert winner == "party"

def test_run_combat_returns_enemies_when_the_party_is_defeated(monkeypatch, make_player, make_monster, melee_weapon):
    monkeypatch.setattr("random.randint", lambda a, b: 15)
    defender = make_player(ac = 1)
    defender.hp = 1
    defender.weapons = [] # cannot fight back
    enemy = make_monster()
    enemy.weapons = [melee_weapon()]

    winner = run_combat([defender], [enemy], log = False)

    assert winner == "enemies"

def test_run_combat_returns_draw_when_neither_side_can_deal_damage(make_player, make_monster):
    passive_player = make_player()
    passive_player.weapons = []
    passive_monster = make_monster()
    passive_monster.weapons = []

    winner = run_combat([passive_player], [passive_monster], log = False)

    assert winner == "draw"

# --- monte_carlo: aggregation, independent of actual combat mechanics ---

def test_monte_carlo_aggregates_percentages_correctly(monkeypatch):
    outcomes = iter(["party", "party", "party", "enemies", "draw"])
    monkeypatch.setattr(combat, "run_combat", lambda party, enemies, log: next(outcomes))

    results = monte_carlo([], [], n = 5, log = False)

    assert results == {"party_win_pct": 60.0, "enemy_win_pct": 20.0, "draw_pct": 20.0, "n": 5}
