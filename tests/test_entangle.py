from pathlib import Path

import pytest

from actions import ActionResult, cast_spell
from combat import log_action
from combatant import AbilityScores
from data import load_spells
from dice import resolve_advantage
from effects import Barkskin, Concentrating, Restrained
from enums import ActionType, Ability, DamageType, RollType, TargetType
from policy_beliefupdating import BeliefUpdatingPolicy
from spell import Spell
from world import Grid, CombatState

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def entangle():
    return load_spells(str(REPO_ROOT / "spells.json"))["Entangle"]

def _state(*placed):
    """Combatants given as (combatant, x, y)."""
    grid = Grid(10, 10)
    for combatant, x, y in placed:
        grid.place(combatant, x, y)
    return CombatState(grid = grid, initiative_order = [c for c, _, _ in placed])

# --- the spell, as the SRD describes it ---

def test_entangle_is_an_area_concentration_spell_with_a_strength_save_that_restrains(entangle):
    assert entangle.level == 1 and entangle.range == 90
    assert entangle.concentration is True
    assert entangle.save_allowed is True and entangle.save_attribute == Ability.STRENGTH
    assert entangle.aoe_radius > 0
    assert entangle.effect is Restrained
    assert entangle.target_type == TargetType.ENEMY
    assert entangle.damage_dice == 0

# --- the Restrained condition: speed 0, attackers have advantage, its attacks have disadvantage, disadvantage on DEX saves ---

def test_a_restrained_creature_has_no_movement_on_its_turn(make_monster):
    monster = make_monster(speed = 40)
    monster.add_effect(Restrained())

    monster.start_turn()

    assert monster.movement == 0

def test_a_creature_that_stops_being_restrained_moves_normally_again(make_monster):
    monster = make_monster(speed = 40)
    restrained = Restrained()
    monster.add_effect(restrained)
    monster.remove_effect(restrained)

    monster.start_turn()

    assert monster.movement == 40

def test_attacks_against_a_restrained_creature_have_advantage_and_its_own_attacks_have_disadvantage(make_player, make_monster):
    attacker, restrained = make_player(), make_monster()
    restrained.add_effect(Restrained())

    assert resolve_advantage(attacker, RollType.ATTACK, other = restrained) == (True, False)
    assert resolve_advantage(restrained, RollType.ATTACK, other = attacker) == (False, True)

def test_a_restrained_creature_has_disadvantage_on_dexterity_saves_only(make_monster):
    restrained = make_monster()
    restrained.add_effect(Restrained())

    assert resolve_advantage(restrained, RollType.SAVE, ability = Ability.DEXTERITY) == (False, True)
    assert resolve_advantage(restrained, RollType.SAVE, ability = Ability.STRENGTH) == (False, False)
    assert resolve_advantage(restrained, RollType.SAVE, ability = Ability.WISDOM) == (False, False)

# --- one cast, several targets, one concentration ---

def _caster_and_enemies(make_player, make_monster, enemy_count = 3):
    caster = make_player(name = "Druid")
    caster.spell_slots = {1: 4}
    enemies = [make_monster(name = f"Enemy {i + 1}") for i in range(enemy_count)]
    return caster, enemies

def test_entangle_restrains_every_enemy_that_fails_its_save(monkeypatch, make_player, make_monster, entangle):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1) # every save fails
    caster, enemies = _caster_and_enemies(make_player, make_monster)
    state = _state((caster, 0, 0), *[(e, 5 + i, 5) for i, e in enumerate(enemies)])

    cast_spell(caster, enemies[0], entangle, state)

    assert all(e.has_effect(Restrained) for e in enemies)

def test_entangle_leaves_an_enemy_that_saves_unrestrained(monkeypatch, make_player, make_monster, entangle):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 20) # every save succeeds
    caster, enemies = _caster_and_enemies(make_player, make_monster)
    state = _state((caster, 0, 0), *[(e, 5 + i, 5) for i, e in enumerate(enemies)])

    cast_spell(caster, enemies[0], entangle, state)

    assert not any(e.has_effect(Restrained) for e in enemies)
    assert not caster.has_effect(Concentrating) # nothing took hold, so there is nothing to concentrate on

def test_the_whole_area_is_held_by_a_single_concentration(monkeypatch, make_player, make_monster, entangle):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    caster, enemies = _caster_and_enemies(make_player, make_monster)
    state = _state((caster, 0, 0), *[(e, 5 + i, 5) for i, e in enumerate(enemies)])

    cast_spell(caster, enemies[0], entangle, state)

    assert sum(isinstance(e, Concentrating) for e in caster.effects) == 1

def test_ending_concentration_frees_everyone_who_was_entangled(monkeypatch, make_player, make_monster, entangle):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    caster, enemies = _caster_and_enemies(make_player, make_monster)
    state = _state((caster, 0, 0), *[(e, 5 + i, 5) for i, e in enumerate(enemies)])
    cast_spell(caster, enemies[0], entangle, state)

    caster.remove_effect(next(e for e in caster.effects if isinstance(e, Concentrating)))

    assert not any(e.has_effect(Restrained) for e in enemies)

def test_a_failed_concentration_save_frees_everyone_who_was_entangled(monkeypatch, make_player, make_monster, entangle):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1) # the concentration save fails too
    caster, enemies = _caster_and_enemies(make_player, make_monster)
    state = _state((caster, 0, 0), *[(e, 5 + i, 5) for i, e in enumerate(enemies)])
    cast_spell(caster, enemies[0], entangle, state)

    caster.take_damage(15, DamageType.SLASHING)

    assert not caster.has_effect(Concentrating)
    assert not any(e.has_effect(Restrained) for e in enemies)

def test_casting_another_concentration_spell_frees_everyone_who_was_entangled(monkeypatch, make_player, make_monster, entangle):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    caster, enemies = _caster_and_enemies(make_player, make_monster)
    caster.spell_slots = {1: 4, 2: 3}
    state = _state((caster, 0, 0), *[(e, 5 + i, 5) for i, e in enumerate(enemies)])
    cast_spell(caster, enemies[0], entangle, state)
    barkskin = Spell(name = "Barkskin", level = 2, target_type = TargetType.ALLY, damage_type = None, damage_dice = 0, damage_sides = 0,
                     range = 5, requires_attack_roll = False, save_allowed = False, save_attribute = Ability.DEXTERITY, effect = Barkskin, concentration = True)

    cast_spell(caster, caster, barkskin, state)

    assert not any(e.has_effect(Restrained) for e in enemies)
    assert caster.has_effect(Barkskin)

# --- breaking free costs the restrained creature's action ---

def _restrained(make_monster, weapon = None, strength = 10, dc = 12):
    monster = make_monster(ability_scores = AbilityScores(strength = strength), name = "Held")
    if weapon is not None:
        monster.weapons = [weapon]
    effect = Restrained(save_dc = dc)
    monster.add_effect(effect)
    monster.start_turn()
    return monster, effect

def test_a_restrained_creature_with_nobody_in_reach_spends_its_action_breaking_free(monkeypatch, make_player, make_monster, melee_weapon):
    monkeypatch.setattr("random.randint", lambda a, b: 20)
    held, effect = _restrained(make_monster, melee_weapon())
    far_away = make_player(name = "Far")
    state = _state((held, 0, 0), (far_away, 8, 0))

    results = held.ai.take_turn(state)

    assert [r.action_type for r in results if r.action_type != ActionType.NONE] == [ActionType.BREAK_FREE]
    assert results[0].save_succeeded is True
    assert not held.has_effect(Restrained)
    assert held.has_action is False

def test_a_failed_attempt_leaves_the_creature_restrained(monkeypatch, make_player, make_monster, melee_weapon):
    monkeypatch.setattr("random.randint", lambda a, b: 1)
    held, effect = _restrained(make_monster, melee_weapon())
    state = _state((held, 0, 0), (make_player(name = "Far"), 8, 0))

    results = held.ai.take_turn(state)

    assert results[0].action_type == ActionType.BREAK_FREE and results[0].save_succeeded is False
    assert held.has_effect(Restrained)

@pytest.mark.parametrize("strength, succeeds", [(18, True), (10, False)]) # d20 roll of 8: +4 makes 12 (a success against DC 12), +0 makes 8
def test_breaking_free_is_a_strength_check_against_the_spells_save_dc(monkeypatch, make_player, make_monster, melee_weapon, strength, succeeds):
    monkeypatch.setattr("random.randint", lambda a, b: 8)
    held, effect = _restrained(make_monster, melee_weapon(), strength = strength, dc = 12)
    state = _state((held, 0, 0), (make_player(name = "Far"), 8, 0))

    results = held.ai.take_turn(state)

    assert results[0].save_succeeded is succeeds

def test_a_restrained_creature_with_a_target_in_reach_attacks_instead_of_struggling(monkeypatch, make_player, make_monster, melee_weapon):
    monkeypatch.setattr("random.randint", lambda a, b: 15)
    held, effect = _restrained(make_monster, melee_weapon())
    adjacent = make_player(name = "Adjacent")
    state = _state((held, 0, 0), (adjacent, 1, 0))

    results = held.ai.take_turn(state)

    assert ActionType.ATTACK in [r.action_type for r in results]
    assert ActionType.BREAK_FREE not in [r.action_type for r in results]
    assert held.has_effect(Restrained)

def test_a_creature_that_is_not_restrained_never_tries_to_break_free(monkeypatch, make_player, make_monster, melee_weapon):
    monkeypatch.setattr("random.randint", lambda a, b: 15)
    free = make_monster(name = "Free")
    free.weapons = [melee_weapon()]
    free.start_turn()
    state = _state((free, 0, 0), (make_player(name = "Far"), 8, 0))

    results = free.ai.take_turn(state)

    assert ActionType.BREAK_FREE not in [r.action_type for r in results]

# --- the log ---

def test_the_log_reports_a_successful_and_a_failed_struggle(make_monster):
    held = make_monster(name = "Held")
    freed =ActionResult(action_type = ActionType.BREAK_FREE, target = held, actor = "Held", effect_applied = "Restrained", save_succeeded = True)
    stuck = ActionResult(action_type = ActionType.BREAK_FREE, target = held, actor = "Held", effect_applied = "Restrained", save_succeeded = False)

    assert log_action(held, [freed]) == ["Held struggles against Restrained - breaks free."]
    assert log_action(held, [stuck]) == ["Held struggles against Restrained - and fails."]

# --- how the scorer treats the spell ---

def test_a_target_that_is_already_restrained_gains_nothing_from_being_entangled_again(make_player, make_monster, entangle):
    caster, target = make_player(), make_monster()
    state = _state((caster, 0, 0), (target, 3, 0))
    policy = BeliefUpdatingPolicy()

    before = policy._spell_hit_terms(caster, target, entangle, state, {})
    target.add_effect(Restrained())
    after = policy._spell_hit_terms(caster, target, entangle, state, {})

    assert before["control_value"] > 0
    assert after == {"control_value": 0.0}

def test_entangling_your_own_side_counts_against_the_spell_as_friendly_fire(make_player, make_monster, entangle):
    caster = make_monster(name = "Druid")
    ally = make_monster(name = "Ally")
    enemy = make_player(name = "Enemy")
    state = _state((caster, 0, 0), (ally, 3, 0), (enemy, 3, 1))
    policy = BeliefUpdatingPolicy()

    assert set(policy._spell_hit_terms(caster, ally, entangle, state, {})) == {"friendly_fire"}
    assert policy._spell_hit_terms(caster, ally, entangle, state, {})["friendly_fire"] < 0
