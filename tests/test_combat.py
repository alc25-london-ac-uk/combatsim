from belief import CombatantBelief, belief_for
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

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 8, mitigated_amount = 8, attack_result = AttackResult.HIT)
    broadcast_observations(actor, [result], combat_state)

    for observer in (actor, bystander):
        belief = observer.ai.beliefs[target]
        assert abs(belief.expected_hp() - (belief.believed_max_hp - 8)) < 1e-9

def test_broadcast_observations_applies_healing_not_damage_when_the_result_is_healing(make_player, make_combat_state):
    healer = make_player()
    ally = make_player(name = "Ally")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(healer, ally, bystander)

    damage_result = ActionResult(action_type = ActionType.ATTACK, target = ally, amount = 10, mitigated_amount = 10, attack_result = AttackResult.HIT)
    broadcast_observations(healer, [damage_result], combat_state)
    damaged_expected_hp = bystander.ai.beliefs[ally].expected_hp()

    heal_result = ActionResult(action_type = ActionType.SPELL, target = ally, amount = 4, attack_result = AttackResult.HIT, is_healing = True)
    broadcast_observations(healer, [heal_result], combat_state)

    assert abs(bystander.ai.beliefs[ally].expected_hp() - (damaged_expected_hp + 4)) < 1e-9

def test_broadcast_observations_does_not_update_the_targets_own_belief_about_themselves(make_player, make_monster, make_combat_state):
    actor = make_player()
    target = make_monster()
    combat_state = make_combat_state(actor, target)

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 5, mitigated_amount = 5, attack_result = AttackResult.HIT)
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

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, mitigated_amount = 6, attack_result = AttackResult.HIT, is_healing = False)
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
        ActionResult(action_type = ActionType.SPELL, target = target_a, amount = 10, mitigated_amount = 10, attack_result = AttackResult.HIT, is_healing = False),
        ActionResult(action_type = ActionType.SPELL, target = target_b, amount = 10, mitigated_amount = 10, attack_result = AttackResult.HIT, is_healing = False),
    ]
    broadcast_observations(caster, results, combat_state)

    # one cast witnessed (even though it hit two targets) should match the single-observation worked example, 0.5 -> 0.95
    assert abs(bystander.ai.beliefs[caster].offensive_capable - 0.95) < 1e-9

def test_broadcast_observations_does_not_update_the_casters_own_belief_about_themselves(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    combat_state = make_combat_state(caster, target)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, mitigated_amount = 6, attack_result = AttackResult.HIT, is_healing = False)
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

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, mitigated_amount = 6, attack_result = AttackResult.HIT, concentration = False)
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

    damage_result = ActionResult(action_type = ActionType.ATTACK, target = caster, amount = 10, mitigated_amount = 10, attack_result = AttackResult.HIT)
    broadcast_observations(target, [damage_result], combat_state)

    assert abs(bystander.ai.beliefs[caster].concentrating - (0.95 * 0.625)) < 1e-9

# --- broadcast_observations: spell-slot depletion evidence attributes to the caster ---

def test_broadcast_observations_updates_the_casters_depletion_belief_for_a_leveled_spell(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 6, mitigated_amount = 6, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3)
    broadcast_observations(caster, [result], combat_state)

    assert abs(bystander.ai.beliefs[caster].depleted - 0.3) < 1e-9

def test_broadcast_observations_does_not_raise_depletion_belief_for_a_cantrip(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target, bystander)

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 4, mitigated_amount = 4, attack_result = AttackResult.HIT, spell = "Fire Bolt", spell_level = 0)
    broadcast_observations(caster, [result], combat_state)

    assert bystander.ai.beliefs[caster].depleted == 0.0

def test_broadcast_observations_counts_an_aoe_leveled_spell_as_one_cast_not_one_per_target(make_player, make_monster, make_combat_state):
    caster = make_player()
    target_a = make_monster(name = "A")
    target_b = make_monster(name = "B")
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(caster, target_a, target_b, bystander)

    results = [
        ActionResult(action_type = ActionType.SPELL, target = target_a, amount = 10, mitigated_amount = 10, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3),
        ActionResult(action_type = ActionType.SPELL, target = target_b, amount = 10, mitigated_amount = 10, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3),
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
        ActionResult(action_type = ActionType.SPELL, target = target, amount = 10, mitigated_amount = 10, attack_result = AttackResult.HIT, spell = "Fireball", spell_level = 3),
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

def test_an_attack_that_drops_the_target_below_zero_reports_it_dead_not_its_negative_hp(make_player):
    attacker = make_player(name = "Attacker")
    target = make_player(name = "Target")
    killing_blow = ActionResult(action_type = ActionType.ATTACK, target = target, actor = "Attacker", weapon = "Sword", amount = 30, attack_result = AttackResult.HIT, target_hp_after_action = -22)

    text = format_attack_result(attacker, killing_blow)

    assert text == "Attacker attacks Target with Sword - 30 damage. Target is dead."

def test_a_target_left_at_exactly_zero_hp_is_dead(make_player):
    attacker = make_player(name = "Attacker")
    target = make_player(name = "Target")
    result = ActionResult(action_type = ActionType.ATTACK, target = target, actor = "Attacker", weapon = "Sword", amount = 5, attack_result = AttackResult.HIT, target_hp_after_action = 0)

    assert format_attack_result(attacker, result).endswith("Target is dead.")

def test_a_target_left_alive_still_reports_its_remaining_hp(make_player):
    attacker = make_player(name = "Attacker")
    target = make_player(name = "Target")
    result = ActionResult(action_type = ActionType.ATTACK, target = target, actor = "Attacker", weapon = "Sword", amount = 5, attack_result = AttackResult.HIT, target_hp_after_action = 1)

    assert format_attack_result(attacker, result).endswith("Target has 1 HP remaining.")

def test_a_spell_that_kills_reports_the_target_dead(make_player):
    caster = make_player(name = "Wizard")
    target = make_player(name = "Ant")
    result = _spell_hit(target)
    result.target_hp_after_action = -9

    lines = log_action(caster, [result])

    assert lines[0] == "Wizard casts Fireball on Ant - 8 damage. Ant is dead."

def test_each_target_of_a_multi_target_spell_is_reported_dead_or_alive_individually(make_player):
    caster = make_player(name = "Wizard")
    dead, alive = make_player(name = "Ant"), make_player(name = "Bee")
    killed, survived = _spell_hit(dead), _spell_hit(alive)
    killed.target_hp_after_action = -3

    lines = log_action(caster, [killed, survived])

    assert "  Ant - 8 damage. Ant is dead." in lines
    assert "  Bee - 8 damage. Bee has 12 HP remaining." in lines

def test_an_opportunity_attack_is_reported_as_one(make_player):
    mover = make_player(name = "Mover")
    result = ActionResult(
        action_type = ActionType.ATTACK, target = mover, actor = "Reactor", weapon = "Sword", amount = 7,
        attack_result = AttackResult.HIT, target_hp_after_action = 10, opportunity_attack = True
    )

    assert format_attack_result(mover, result) == "Reactor makes an opportunity attack on Mover with Sword - 7 damage. Mover has 10 HP remaining."

def test_an_ordinary_attack_is_not_reported_as_an_opportunity_attack(make_player):
    attacker = make_player(name = "Attacker")
    target = make_player(name = "Target")
    result = ActionResult(action_type = ActionType.ATTACK, target = target, actor = "Attacker", weapon = "Sword", attack_result = AttackResult.MISS)

    assert "opportunity" not in format_attack_result(attacker, result)

def test_log_action_reports_none_action_as_skipped(make_player):
    turn_holder = make_player(name = "Idle")
    result = ActionResult(action_type = ActionType.NONE, target = turn_holder)

    lines = log_action(turn_holder, [result])

    assert lines == ["Idle skipped their turn."]

# --- log_action: movement, skipped turns and multi-target spells ---

def _move(target, x, y):
    return ActionResult(action_type = ActionType.MOVE, target = target, combatant_x = x, combatant_y = y)

def _attack(target, actor = "Mover"):
    return ActionResult(action_type = ActionType.ATTACK, target = target, actor = actor, weapon = "Sword", attack_result = AttackResult.MISS, rationale = "closest")

def _spell_hit(target, spell = "Fireball", actor = "Wizard"):
    return ActionResult(action_type = ActionType.SPELL, target = target, actor = actor, spell = spell, amount = 8, attack_result = AttackResult.HIT, target_hp_after_action = 12, rationale = "best score")

def test_a_single_step_is_logged_without_a_path(make_player):
    mover = make_player(name = "Mover")

    assert log_action(mover, [_move(mover, 4, 8)]) == ["Mover moved to 4,8"]

def test_consecutive_steps_are_logged_as_one_move_listing_the_squares_passed(make_player):
    mover = make_player(name = "Mover")
    steps = [_move(mover, 4, 8), _move(mover, 3, 7), _move(mover, 2, 6), _move(mover, 1, 5)]

    assert log_action(mover, steps) == ["Mover moved to 1,5 (via 4,8, 3,7, 2,6)"]

def test_steps_either_side_of_an_attack_are_logged_as_separate_moves(make_player):
    mover = make_player(name = "Mover")
    target = make_player(name = "Target")

    lines = log_action(mover, [_move(mover, 1, 1), _attack(target), _move(mover, 2, 2)])

    assert lines[0] == "Mover moved to 1,1"
    assert lines[1].startswith("Mover attacks Target")
    assert lines[-1] == "Mover moved to 2,2"

def test_an_unused_bonus_action_after_an_attack_is_not_logged_as_a_skipped_turn(make_player):
    mover = make_player(name = "Mover")
    target = make_player(name = "Target")
    no_bonus_action = ActionResult(action_type = ActionType.NONE, target = mover)

    lines = log_action(mover, [_attack(target), no_bonus_action])

    assert not any("skipped" in line for line in lines)

def test_a_turn_spent_only_moving_is_not_logged_as_skipped_even_with_no_other_action(make_player):
    mover = make_player(name = "Mover")
    no_bonus_action = ActionResult(action_type = ActionType.NONE, target = mover)

    lines = log_action(mover, [_move(mover, 1, 1), no_bonus_action])

    assert lines == ["Mover moved to 1,1"]

def test_a_turn_with_nothing_to_do_is_logged_as_skipped_only_once(make_player):
    idle = make_player(name = "Idle")
    nothing = ActionResult(action_type = ActionType.NONE, target = idle)

    assert log_action(idle, [nothing, nothing]) == ["Idle skipped their turn."]

def test_a_turn_lost_to_an_effect_names_the_effect(make_player):
    held = make_player(name = "Held")
    lost = ActionResult(action_type = ActionType.NONE, target = held, rationale = "Paralysed")

    assert log_action(held, [lost]) == ["Held is paralysed and loses their turn."]

def test_a_spell_that_hit_several_targets_is_one_heading_with_an_indented_line_per_target(make_player):
    targets = [make_player(name = name) for name in ("Ant", "Bee", "Cat")]

    lines = log_action(make_player(name = "Wizard"), [_spell_hit(t) for t in targets])

    assert lines[0] == "Wizard casts Fireball:"
    assert [line for line in lines if line.startswith("  ")] == [
        "  Ant - 8 damage. Ant has 12 HP remaining.",
        "  Bee - 8 damage. Bee has 12 HP remaining.",
        "  Cat - 8 damage. Cat has 12 HP remaining.",
    ]

def test_a_multi_target_spell_logs_its_rationale_once(make_player):
    targets = [make_player(name = name) for name in ("Ant", "Bee")]

    lines = log_action(make_player(name = "Wizard"), [_spell_hit(t) for t in targets])

    assert [line for line in lines if line.strip().startswith("->")] == [" -> best score"]

def test_a_spell_with_one_target_stays_on_one_line(make_player):
    target = make_player(name = "Ant")

    lines = log_action(make_player(name = "Wizard"), [_spell_hit(target)])

    assert lines[0] == "Wizard casts Fireball on Ant - 8 damage. Ant has 12 HP remaining."
    assert not any(line.startswith("  ") for line in lines)

def test_two_different_spells_in_one_turn_are_not_grouped(make_player):
    target = make_player(name = "Ant")

    lines = log_action(make_player(name = "Wizard"), [_spell_hit(target, "Fireball"), _spell_hit(target, "Shield of Faith")])

    assert lines[0].startswith("Wizard casts Fireball on Ant")
    assert any(line.startswith("Wizard casts Shield of Faith on Ant") for line in lines)

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


# --- broadcast_observations: AC and save evidence ---

def test_broadcast_observations_teammates_of_the_actor_learn_the_targets_ac(make_player, make_monster, make_combat_state):
    actor = make_player(name = "Actor")
    teammate = make_player(name = "Teammate")
    target = make_monster()
    combat_state = make_combat_state(actor, teammate, target)
    prior_ac = CombatantBelief.initial_prior_for(target).expected_armour_class()

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 0, attack_result = AttackResult.MISS, attack_roll_bonus = 5)
    broadcast_observations(actor, [result], combat_state)

    assert teammate.ai.beliefs[target].expected_armour_class() > prior_ac
    assert actor.ai.beliefs[target].expected_armour_class() > prior_ac

def test_broadcast_observations_the_targets_side_does_not_learn_from_the_attackers_rolls(make_player, make_monster, make_combat_state):
    actor = make_player(name = "Actor")
    target = make_monster(name = "Target")
    target_ally = make_monster(name = "Target Ally")
    combat_state = make_combat_state(actor, target, target_ally)

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 0, attack_result = AttackResult.MISS, attack_roll_bonus = 5)
    broadcast_observations(actor, [result], combat_state)

    assert target not in target_ally.ai.beliefs

def test_broadcast_observations_ignores_critical_hits_for_ac_inference(make_player, make_monster, make_combat_state):
    actor = make_player(name = "Actor")
    target = make_monster()
    combat_state = make_combat_state(actor, target)
    prior = CombatantBelief.initial_prior_for(target).ac_distribution

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 9, attack_result = AttackResult.CRIT, attack_roll_bonus = 5)
    broadcast_observations(actor, [result], combat_state)

    assert actor.ai.beliefs[target].ac_distribution == prior

def test_broadcast_observations_updates_save_beliefs_from_a_rolled_save(make_player, make_monster, make_combat_state):
    from enums import Ability

    actor = make_player(name = "Actor")
    target = make_monster()
    combat_state = make_combat_state(actor, target)
    prior = CombatantBelief.initial_prior_for(target)
    prior_mean = sum(m * p for m, p in prior.save_modifier_distribution(Ability.WISDOM).items())

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 0, spell = "Hold Person", save_ability = Ability.WISDOM, save_dc = 14, save_succeeded = True)
    broadcast_observations(actor, [result], combat_state)

    updated = actor.ai.beliefs[target]
    assert sum(m * p for m, p in updated.save_modifier_distribution(Ability.WISDOM).items()) > prior_mean


# --- broadcast_observations: HP belief follows damage actually taken ---

def test_broadcast_observations_hp_belief_uses_damage_taken_for_a_resisted_hit(make_player, make_monster, make_combat_state):
    attacker = make_player()
    target = make_monster(max_hp = 40)
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(attacker, target, bystander)
    before = CombatantBelief.initial_prior_for(target).expected_hp()

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 10, mitigated_amount = 5, attack_result = AttackResult.HIT, damage_type = DamageType.SLASHING)
    broadcast_observations(attacker, [result], combat_state)

    assert abs(bystander.ai.beliefs[target].expected_hp() - (before - 5)) < 1e-6

def test_broadcast_observations_hp_belief_is_unchanged_by_an_immune_hit(make_player, make_monster, make_combat_state):
    attacker = make_player()
    target = make_monster(max_hp = 40)
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(attacker, target, bystander)
    before = CombatantBelief.initial_prior_for(target).expected_hp()

    result = ActionResult(action_type = ActionType.SPELL, target = target, amount = 12, mitigated_amount = 0, attack_result = AttackResult.HIT, damage_type = DamageType.FIRE)
    broadcast_observations(attacker, [result], combat_state)

    assert abs(bystander.ai.beliefs[target].expected_hp() - before) < 1e-6

def test_broadcast_observations_an_immune_hit_does_not_decay_the_concentration_belief(make_player, make_monster, make_combat_state):
    attacker = make_monster(name = "Attacker")
    caster = make_player()
    bystander = make_monster(name = "Bystander")
    combat_state = make_combat_state(attacker, caster, bystander)
    bystander.ai.beliefs[caster] = CombatantBelief.initial_prior_for(caster)
    bystander.ai.beliefs[caster].concentrating = 0.95

    result = ActionResult(action_type = ActionType.ATTACK, target = caster, amount = 12, mitigated_amount = 0, attack_result = AttackResult.HIT, damage_type = DamageType.FIRE)
    broadcast_observations(attacker, [result], combat_state)

    assert abs(bystander.ai.beliefs[caster].concentrating - 0.95) < 1e-9

def test_broadcast_observations_hp_belief_uses_the_doubled_damage_for_a_vulnerable_hit(make_player, make_monster, make_combat_state):
    attacker = make_player()
    target = make_monster(max_hp = 60)
    bystander = make_player(name = "Bystander")
    combat_state = make_combat_state(attacker, target, bystander)
    before = CombatantBelief.initial_prior_for(target).expected_hp()

    result = ActionResult(action_type = ActionType.ATTACK, target = target, amount = 7, mitigated_amount = 14, attack_result = AttackResult.HIT, damage_type = DamageType.BLUDGEONING)
    broadcast_observations(attacker, [result], combat_state)

    assert abs(bystander.ai.beliefs[target].expected_hp() - (before - 14)) < 1e-6


def test_broadcast_observations_a_teammates_ac_evidence_about_one_skeleton_carries_to_its_siblings(make_player, make_monster, make_combat_state):
    actor = make_player(name = "Actor")
    first = make_monster(name = "Skeleton 1")
    first.type_name = "Skeleton"
    second = make_monster(name = "Skeleton 2")
    second.type_name = "Skeleton"
    combat_state = make_combat_state(actor, first, second)
    prior = CombatantBelief.initial_prior_for(second).expected_armour_class()

    result = ActionResult(action_type = ActionType.ATTACK, target = first, amount = 0, attack_result = AttackResult.MISS, attack_roll_bonus = 5)
    broadcast_observations(actor, [result], combat_state)

    assert belief_for(actor.ai.beliefs, second).expected_armour_class() > prior
