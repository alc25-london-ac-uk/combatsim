from typing import Any

from combatant import PlayerCharacter, Monster, AbilityScores
from weapon import MeleeWeapon, RangedWeapon
from spell import Spell
from world import Grid, CombatState
from enums import AttackResult, Ability, DamageType, TargetType
from actions import attack, cast_spell, move_towards_target
from effects import Barkskin, Concentrating, Paralysed

def _make_player(**overrides):
    defaults: dict[str, Any] = dict(
        name = "Test Player",
        ac = 15,
        ability_scores = AbilityScores(),
        character_class = "fighter",
        level = 5,
        team = "party"
    )
    defaults.update(overrides)
    player = PlayerCharacter(**defaults)
    player.hp = player.max_hp
    return player

def _make_monster(**overrides):
    defaults: dict[str, Any] = dict(
        name = "Test Monster",
        ac = 12,
        ability_scores = AbilityScores(),
        max_hp = 20,
        attack_bonus = 3,
        team = "enemies"
    )
    defaults.update(overrides)
    monster = Monster(**defaults)
    monster.hp = monster.max_hp
    return monster

def _melee_weapon():
    return MeleeWeapon(name = "Test Sword", damage_dice = 1, damage_sides = 6, damage_type = DamageType.SLASHING, reach = 5, finesse = False)

def _ranged_weapon():
    return RangedWeapon(name = "Test Bow", damage_dice = 1, damage_sides = 6, damage_type = DamageType.PIERCING, optimal_distance = 80, maximum_distance = 320)

def _combat_state(*combatants):
    grid = Grid(10, 10)
    for c in combatants:
        grid.place(c, 0, 0)
    return CombatState(grid = grid, initiative_order = list(combatants))

# --- attack() ---

def test_attack_hit_applies_damage(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 15)
    attacker = _make_player()
    target = _make_monster(ac = 10)
    combat_state = _combat_state(attacker, target)

    attack_result, amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.HIT
    assert amount > 0
    assert target.hp == target.max_hp - amount

def test_attack_miss_deals_no_damage(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    attacker = _make_player()
    target = _make_monster(ac = 25)
    combat_state = _combat_state(attacker, target)

    attack_result, amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.MISS
    assert amount == 0
    assert target.hp == target.max_hp

def test_attack_crit_doubles_dice_but_not_ability_modifier(monkeypatch):
    # crits should only double the dice rolled, not the flat ability modifier added on top
    monkeypatch.setattr("dice.random.randint", lambda a, b: 20)
    attacker = _make_player(ability_scores = AbilityScores(strength = 16)) # +3 STR mod
    target = _make_monster(ac = 10)
    combat_state = _combat_state(attacker, target)

    attack_result, amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.CRIT
    assert amount == 20 * 2 + 3 # dice doubled, modifier added once

def test_melee_attack_against_paralysed_target_is_always_a_crit(monkeypatch):
    # a roll of 1 would normally always miss -- Paralysed forces an auto-crit regardless of the roll, for melee attacks specifically
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    attacker = _make_player()
    target = _make_monster(ac = 25)
    target.add_effect(Paralysed())
    combat_state = _combat_state(attacker, target)

    attack_result, amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.CRIT
    assert amount > 0

def test_ranged_attack_against_paralysed_target_does_not_auto_crit(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    attacker = _make_player()
    target = _make_monster(ac = 25)
    target.add_effect(Paralysed())
    combat_state = _combat_state(attacker, target)

    attack_result, amount = attack(attacker, target, _ranged_weapon(), combat_state)

    assert attack_result == AttackResult.MISS

# --- cast_spell() ---

def test_healing_spell_heals_instead_of_damaging(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player()
    target = _make_player(name = "Ally")
    target.hp = 5
    combat_state = _combat_state(caster, target)

    cure_wounds = Spell(
        name = "Cure Wounds", level = 1, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    caster.spell_slots = {1: 1}

    attack_result, amount, save_made, effect_applied = cast_spell(caster, target, cure_wounds, combat_state)

    assert amount > 0
    assert target.hp == 5 + amount

def test_healing_does_not_exceed_max_hp(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 8)
    caster = _make_player()
    target = _make_player(name = "Ally")
    combat_state = _combat_state(caster, target)

    cure_wounds = Spell(
        name = "Cure Wounds", level = 1, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 1, damage_sides = 8, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )
    caster.spell_slots = {1: 1}

    cast_spell(caster, target, cure_wounds, combat_state)

    assert target.hp == target.max_hp

def test_damage_spell_reduces_target_hp(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player()
    target = _make_monster(ac = 5)
    combat_state = _combat_state(caster, target)

    inflict_wounds = Spell(
        name = "Inflict Wounds", level = 1, target_type = TargetType.ENEMY, damage_type = DamageType.NECROTIC,
        damage_dice = 3, damage_sides = 10, range = 5, requires_attack_roll = True,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    caster.spell_slots = {1: 1}

    cast_spell(caster, target, inflict_wounds, combat_state)

    assert target.hp < target.max_hp

def test_casting_a_second_concentration_spell_ends_the_first(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1) # keep any saves/rolls out of the way
    caster = _make_player()
    ally = _make_player(name = "Ally")
    enemy = _make_monster(name = "Enemy")
    combat_state = _combat_state(caster, ally, enemy)

    barkskin_spell = Spell(
        name = "Barkskin", level = 2, target_type = TargetType.ALLY, damage_type = None,
        damage_dice = 0, damage_sides = 0, range = 5, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY, effect = Barkskin, concentration = True
    )
    hold_person_spell = Spell(
        name = "Hold Person", level = 2, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 0, damage_sides = 0, range = 60, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.WISDOM, effect = Paralysed, concentration = True
    )
    caster.spell_slots = {2: 5}

    cast_spell(caster, ally, barkskin_spell, combat_state)
    assert ally.has_effect(Barkskin)
    assert caster.has_effect(Concentrating)

    cast_spell(caster, enemy, hold_person_spell, combat_state)
    assert enemy.has_effect(Paralysed)
    assert caster.has_effect(Concentrating) # still concentrating, just on the new spell
    assert not ally.has_effect(Barkskin) # the first concentration spell ended

def test_cantrip_gains_an_extra_damage_die_at_caster_level_5(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player(level = 5)
    target = _make_monster()
    combat_state = _combat_state(caster, target)

    fire_bolt = Spell(
        name = "Fire Bolt", level = 0, target_type = TargetType.ENEMY, damage_type = DamageType.FIRE,
        damage_dice = 1, damage_sides = 10, range = 120, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )

    _, amount, _, _ = cast_spell(caster, target, fire_bolt, combat_state)

    expected_bonus = caster.get_spell_attack_bonus()
    assert amount == 4 * 2 + expected_bonus # base die + 1 extra die at level 5

def test_cantrip_has_no_extra_die_below_caster_level_5(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player(level = 4)
    target = _make_monster()
    combat_state = _combat_state(caster, target)

    fire_bolt = Spell(
        name = "Fire Bolt", level = 0, target_type = TargetType.ENEMY, damage_type = DamageType.FIRE,
        damage_dice = 1, damage_sides = 10, range = 120, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )

    _, amount, _, _ = cast_spell(caster, target, fire_bolt, combat_state)

    expected_bonus = caster.get_spell_attack_bonus()
    assert amount == 4 * 1 + expected_bonus

# --- move_towards_target() / opportunity attacks ---

def test_leaving_melee_reach_triggers_an_opportunity_attack(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 15)
    mover = _make_player(name = "Mover")
    reactor = _make_monster(name = "Reactor", ac = 5)
    reactor.weapons = [_melee_weapon()]
    far_target = _make_monster(name = "Far Target", ac = 5)

    grid = Grid(10, 10)
    grid.place(mover, 0, 1)
    grid.place(reactor, 0, 0)
    grid.place(far_target, 0, 5)
    combat_state = CombatState(grid = grid, initiative_order = [mover, reactor, far_target])

    results = move_towards_target(mover, far_target, combat_state)

    opportunity_attacks = [r for r in results if r.rationale == "Opportunity attack"]
    assert len(opportunity_attacks) == 1
    assert opportunity_attacks[0].actor == "Reactor"
    assert opportunity_attacks[0].target is mover
    assert reactor.has_reaction is False

def test_no_opportunity_attack_when_reactor_has_no_reaction_left(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 15)
    mover = _make_player(name = "Mover")
    reactor = _make_monster(name = "Reactor", ac = 5)
    reactor.weapons = [_melee_weapon()]
    reactor.has_reaction = False
    far_target = _make_monster(name = "Far Target", ac = 5)

    grid = Grid(10, 10)
    grid.place(mover, 0, 1)
    grid.place(reactor, 0, 0)
    grid.place(far_target, 0, 5)
    combat_state = CombatState(grid = grid, initiative_order = [mover, reactor, far_target])

    results = move_towards_target(mover, far_target, combat_state)

    assert not any(r.rationale == "Opportunity attack" for r in results)

def test_no_opportunity_attack_when_reactor_has_no_melee_weapon(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 15)
    mover = _make_player(name = "Mover")
    reactor = _make_monster(name = "Reactor", ac = 5) # no weapons at all
    far_target = _make_monster(name = "Far Target", ac = 5)

    grid = Grid(10, 10)
    grid.place(mover, 0, 1)
    grid.place(reactor, 0, 0)
    grid.place(far_target, 0, 5)
    combat_state = CombatState(grid = grid, initiative_order = [mover, reactor, far_target])

    results = move_towards_target(mover, far_target, combat_state)

    assert not any(r.rationale == "Opportunity attack" for r in results)

def test_no_opportunity_attack_when_moving_towards_the_reactor(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 15)
    mover = _make_player(name = "Mover")
    reactor = _make_monster(name = "Reactor", ac = 5)
    reactor.weapons = [_melee_weapon()]

    grid = Grid(10, 10)
    grid.place(mover, 0, 5) # starts well outside the reactor's reach
    grid.place(reactor, 0, 0)
    combat_state = CombatState(grid = grid, initiative_order = [mover, reactor])

    results = move_towards_target(mover, reactor, combat_state) # moving towards, not away

    assert not any(r.rationale == "Opportunity attack" for r in results)
