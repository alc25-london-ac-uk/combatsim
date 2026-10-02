import combat
from combat import format_attack_result, format_spell_result, log_action, run_combat, monte_carlo, broadcast_observations
from actions import ActionResult
from enums import ActionType, AttackResult, DamageType

# --- broadcast_observations: routes damage vs healing to the right belief update ---

def test_broadcast_observations_applies_damage_to_every_other_observers_belief(make_player, make_monster, make_combat_state):
    actor = make_player()
    target = make_monster(max_hp = 20)
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(actor, target, bystander)

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 8, attack_result = AttackResult.HIT)
    broadcast_observations(actor, [result], combat_state)

    for observer in (actor, bystander):
        belief = observer.ai.beliefs[target]
        assert abs(belief.expected_hp() - (belief.believed_max_hp - 8)) < 1e-9

def test_broadcast_observations_applies_healing_not_damage_when_the_result_is_healing(make_player, make_combat_state):
    healer = make_player()
    ally = make_player(name = "Ally")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(healer, ally, bystander)

    damage_result = ActionResult(action_type = ActionType.ATTACK, target = ally, amount = 10, attack_result = AttackResult.HIT)
    broadcast_observations(healer, [damage_result], combat_state)
    damaged_expected_hp = bystander.ai.beliefs[ally].expected_hp()

    heal_result = ActionResult(action_type = ActionType.SPELL, target = ally, amount = 4, attack_result = AttackResult.HIT, is_healing = True)
    broadcast_observations(healer, [heal_result], combat_state)

    assert abs(bystander.ai.beliefs[ally].expected_hp() - (damaged_expected_hp + 4)) < 1e-9

def test_broadcast_observations_does_not_update_the_targets_own_belief_about_themselves(make_player, make_monster, make_combat_state):
    actor = make_player()
    target = make_monster()
    combat_state = make_combat_state(actor, target)

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 5, attack_result = AttackResult.HIT)
    broadcast_observations(actor, [result], combat_state)

    assert target not in target.ai.beliefs

def test_broadcast_observations_ignores_misses_and_moves(make_player, make_monster, make_combat_state):
    actor = make_player()
    target = make_monster()
    combat_state = make_combat_state(actor, target)

    miss_result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 0, attack_result = AttackResult.MISS)
    move_result = ActionResult(action_type = ActionType.MOVE, target = target, amount = 0)
    broadcast_observations(actor, [miss_result, move_result], combat_state)

    assert target not in actor.ai.beliefs

# --- broadcast_observations: spellcasting-role evidence attributes to the caster, not the target ---

def test_broadcast_observations_updates_the_casters_offensive_belief_not_the_targets(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, attack_result = AttackResult.HIT, is_healing = False)
    broadcast_observations(caster, [result], combat_state)

    assert bystander.ai.beliefs[caster].offensive_capable > 0.5
    assert target not in bystander.ai.beliefs or bystander.ai.beliefs[target].offensive_capable == 0.5

def test_broadcast_observations_updates_the_casters_healer_belief_for_a_healing_spell(make_player, make_combat_state):
    caster = make_player()
    ally = make_player(name = "Ally")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, ally, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = ally, amount = 4, attack_result = AttackResult.HIT, is_healing = True)
    broadcast_observations(caster, [result], combat_state)

    assert bystander.ai.beliefs[caster].healer_capable > 0.5
    assert bystander.ai.beliefs[caster].offensive_capable == 0.5

def test_broadcast_observations_counts_an_aoe_spell_as_one_cast_not_one_per_target(make_player, make_monster, make_combat_state):
    caster = make_player()
    target_a = make_monster(name = "A")
    target_b = make_monster(name = "B")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target_a, target_b, bystander)

    results = [
        ActionResult(action_type = ActionType.SPELL, target = target_a, amount = 10, attack_result = AttackResult.HIT, is_healing = False),
        ActionResult(action_type = ActionType.SPELL, target = target_b, amount = 10, attack_result = AttackResult.HIT, is_healing = False),
    ]
    broadcast_observations(caster, results, combat_state)

    # one cast witnessed (even though it hit two targets) should match the single-observation worked example, 0.5 -> 0.95
    assert abs(bystander.ai.beliefs[caster].offensive_capable - 0.95) < 1e-9

def test_broadcast_observations_does_not_update_the_casters_own_belief_about_themselves(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    combat_state = make_combat_state(caster, target)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, attack_result = AttackResult.HIT, is_healing = False)
    broadcast_observations(caster, [result], combat_state)

    assert caster not in caster.ai.beliefs

# --- broadcast_observations: concentration-spell evidence attributes to the caster ---

def test_broadcast_observations_updates_the_casters_concentration_belief_for_a_concentration_spell(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 0, attack_result = AttackResult.HIT, concentration = True)
    broadcast_observations(caster, [result], combat_state)

    assert abs(bystander.ai.beliefs[caster].concentrating - 0.95) < 1e-9

def test_broadcast_observations_does_not_raise_concentration_belief_for_a_non_concentration_spell(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, attack_result = AttackResult.HIT, concentration = False)
    broadcast_observations(caster, [result], combat_state)

    assert bystander.ai.beliefs[caster].concentrating == 0.0

def test_broadcast_observations_counts_an_aoe_concentration_spell_as_one_cast(make_player, make_monster, make_combat_state):
    caster = make_player()
    target_a = make_monster(name = "A")
    target_b = make_monster(name = "B")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target_a, target_b, bystander)

    results = [
        ActionResult(action_type = ActionType.SPELL, target = target_a, amount = 0, attack_result = AttackResult.HIT, concentration = True),
        ActionResult(action_type = ActionType.SPELL, target = target_b, amount = 0, attack_result = AttackResult.HIT, concentration = True),
    ]
    broadcast_observations(caster, results, combat_state)

    assert abs(bystander.ai.beliefs[caster].concentrating - 0.95) < 1e-9

def test_broadcast_observations_decays_concentration_belief_via_the_existing_damage_path(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    cast_result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 0, attack_result = AttackResult.HIT, concentration = True)
    broadcast_observations(caster, [cast_result], combat_state)
    assert abs(bystander.ai.beliefs[caster].concentrating - 0.95) < 1e-9

    damage_result = ActionResult(action_type = ActionType.ATTACK, target = caster, amount = 10, attack_result = AttackResult.HIT)
    broadcast_observations(target, [damage_result], combat_state)

    assert abs(bystander.ai.beliefs[caster].concentrating - (0.95 * 0.625)) < 1e-9

# --- broadcast_observations: spell-slot depletion evidence attributes to the caster ---

def test_broadcast_observations_updates_the_casters_depletion_belief_for_a_leveled_spell(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3)
    broadcast_observations(caster, [result], combat_state)

    assert abs(bystander.ai.beliefs[caster].depleted - 0.3) < 1e-9

def test_broadcast_observations_does_not_raise_depletion_belief_for_a_cantrip(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 4, attack_result = AttackResult.HIT, spell = "Fire Bolt", spell_level = 0)
    broadcast_observations(caster, [result], combat_state)

    assert bystander.ai.beliefs[caster].depleted == 0.0

def test_broadcast_observations_counts_an_aoe_leveled_spell_as_one_cast_not_one_per_target(make_player, make_monster, make_combat_state):
    caster = make_player()
    target_a = make_monster(name = "A")
    target_b = make_monster(name = "B")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target_a, target_b, bystander)

    results = [
        ActionResult(action_type = ActionType.SPELL, target = target_a, amount = 10, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3),
        ActionResult(action_type = ActionType.SPELL, target = target_b, amount = 10, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3),
    ]
    broadcast_observations(caster, results, combat_state)

    assert abs(bystander.ai.beliefs[caster].depleted - 0.3) < 1e-9

def test_broadcast_observations_counts_two_different_leveled_spells_in_one_turn_as_two_casts(make_player, make_monster, make_combat_state):
    # a main action spell and a bonus action spell in the same turn are two separate slot expenditures
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    results = [
        ActionResult(action_type = ActionType.SPELL, target = target, amount = 10, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3),
        ActionResult(action_type = ActionType.SPELL, target = target, amount = 5, attack_result = AttackResult.HIT, spell = "Healing Word", spell_level = 1, is_healing = True),
    ]
    broadcast_observations(caster, results, combat_state)

    assert abs(bystander.ai.beliefs[caster].depleted - 0.51) < 1e-9

# --- broadcast_observations: damage-mitigation evidence attributes to the target ---

def test_broadcast_observations_updates_the_targets_damage_multiplier_belief(make_player, make_monster, make_combat_state):
    actor = make_player()
    target = make_monster(max_hp = 20)
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(actor, target, bystander)

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 10, mitigated_amount = 5, damage_type = DamageType.FIRE, attack_result = AttackResult.HIT)
    broadcast_observations(actor, [result], combat_state)

    for observer in (actor, bystander):
        assert abs(observer.ai.beliefs[target].damage_multiplier(DamageType.FIRE) - 0.75) < 1e-9

def test_broadcast_observations_does_not_update_damage_multiplier_for_healing(make_player, make_combat_state):
    healer = make_player()
    ally = make_player(name = "Ally")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(healer, ally, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = ally, amount = 10, mitigated_amount = 5, damage_type = DamageType.FIRE, attack_result = AttackResult.HIT, is_healing = True)
    broadcast_observations(healer, [result], combat_state)

    assert bystander.ai.beliefs[ally].damage_multiplier(DamageType.FIRE) == 1.0

def test_broadcast_observations_skips_damage_multiplier_update_when_damage_type_is_none(make_player, make_monster, make_combat_state):
    actor = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(actor, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 10, mitigated_amount = 5, damage_type = None, attack_result = AttackResult.HIT)
    broadcast_observations(actor, [result], combat_state)

    # no crash, and no belief created against a damage type we can't identify
    assert bystander.ai.beliefs[target].damage_multipliers == {}

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

    winner, round_num = run_combat([attacker], [enemy], log = False)

    assert winner == "party"
    assert round_num >= 1

def test_run_combat_returns_enemies_when_the_party_is_defeated(monkeypatch, make_player, make_monster, melee_weapon):
    monkeypatch.setattr("random.randint", lambda a, b: 15)
    defender = make_player(ac = 1)
    defender.hp = 1
    defender.weapons = [] # cannot fight back
    enemy = make_monster()
    enemy.weapons = [melee_weapon()]

    winner, round_num = run_combat([defender], [enemy], log = False)

    assert winner == "enemies"
    assert round_num >= 1

def test_run_combat_returns_draw_when_neither_side_can_deal_damage(make_player, make_monster):
    passive_player = make_player()
    passive_player.weapons = []
    passive_monster = make_monster()
    passive_monster.weapons = []

    winner, round_num = run_combat([passive_player], [passive_monster], log = False)

    assert winner == "draw"
    assert round_num == 51 # hits the round cap, since neither side can ever defeat the other

# --- monte_carlo: aggregation, independent of actual combat mechanics ---

def test_monte_carlo_aggregates_percentages_correctly(monkeypatch):
    outcomes = iter([("party", 3), ("party", 5), ("party", 4), ("enemies", 10), ("draw", 51)])
    monkeypatch.setattr(combat, "run_combat", lambda party, enemies, log: next(outcomes))

    results = monte_carlo([], [], n = 5, log = False)

    assert results == {"party_win_pct": 60.0, "enemy_win_pct": 20.0, "draw_pct": 20.0, "average_rounds": 14.6, "n": 5}
