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

    attack_result, amount, mitigated_amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.HIT
    assert amount > 0
    assert target.hp == target.max_hp - amount

def test_attack_against_a_resistant_target_returns_a_smaller_mitigated_amount(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 15)
    attacker = _make_player()
    target = _make_monster(ac = 10, damage_resistances = [DamageType.SLASHING])
    combat_state = _combat_state(attacker, target)

    attack_result, amount, mitigated_amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.HIT
    assert mitigated_amount == amount // 2
    assert target.hp == target.max_hp - mitigated_amount

def test_attack_miss_deals_no_damage(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    attacker = _make_player()
    target = _make_monster(ac = 25)
    combat_state = _combat_state(attacker, target)

    attack_result, amount, mitigated_amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.MISS
    assert amount == 0
    assert target.hp == target.max_hp

def test_attack_crit_doubles_dice_but_not_ability_modifier(monkeypatch):
    # crits should only double the dice rolled, not the flat ability modifier added on top
    monkeypatch.setattr("dice.random.randint", lambda a, b: 20)
    attacker = _make_player(ability_scores = AbilityScores(strength = 16)) # +3 STR mod
    target = _make_monster(ac = 10)
    combat_state = _combat_state(attacker, target)

    attack_result, amount, mitigated_amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.CRIT
    assert amount == 20 * 2 + 3 # dice doubled, modifier added once

def test_melee_attack_against_paralysed_target_is_always_a_crit(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    attacker = _make_player()
    target = _make_monster(ac = 25)
    target.add_effect(Paralysed())
    combat_state = _combat_state(attacker, target)

    attack_result, amount, mitigated_amount = attack(attacker, target, _melee_weapon(), combat_state)

    assert attack_result == AttackResult.CRIT
    assert amount > 0

def test_ranged_attack_against_paralysed_target_does_not_auto_crit(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1)
    attacker = _make_player()
    target = _make_monster(ac = 25)
    target.add_effect(Paralysed())
    combat_state = _combat_state(attacker, target)

    attack_result, amount, mitigated_amount = attack(attacker, target, _ranged_weapon(), combat_state)

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

    spell_hit_results = cast_spell(caster, target, cure_wounds, combat_state)

    assert spell_hit_results[0].amount > 0
    assert target.hp == 5 + spell_hit_results[0].amount

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

def test_damage_spell_with_no_damage_type_still_reduces_target_hp(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player()
    target = _make_monster(ac = 5)
    combat_state = _combat_state(caster, target)

    typeless_spell = Spell(
        name = "Typeless Bolt", level = 1, target_type = TargetType.ENEMY, damage_type = None,
        damage_dice = 3, damage_sides = 10, range = 5, requires_attack_roll = True,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    caster.spell_slots = {1: 1}

    cast_spell(caster, target, typeless_spell, combat_state)

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

    spell_hit_results = cast_spell(caster, target, fire_bolt, combat_state)
    amount = spell_hit_results[0].amount

    assert amount == 4 * 2 # base die + 1 extra die at level 5, and no caster bonus

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

    spell_hit_results = cast_spell(caster, target, fire_bolt, combat_state)
    amount = spell_hit_results[0].amount

    assert amount == 4 * 1

# --- cast_spell() AoE ---

def _fireball(**overrides):
    defaults: dict[str, Any] = dict(
        name = "Fireball", level = 3, target_type = TargetType.ENEMY, damage_type = DamageType.FIRE,
        damage_dice = 8, damage_sides = 6, range = 150, requires_attack_roll = False,
        save_allowed = True, save_attribute = Ability.DEXTERITY, damage_pct_on_save = 0.5,
        aoe_radius = 20
    )
    defaults.update(overrides)
    return Spell(**defaults)

def test_aoe_spell_hits_every_target_within_the_radius(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player(level = 5)
    primary = _make_monster(name = "Primary", ac = 5)
    bystander = _make_monster(name = "Bystander", ac = 5)
    combat_state = _combat_state(caster, primary, bystander) # helper places everyone at (0,0)
    combat_state.grid.place(caster, 30, 0) # keep the caster itself out of their own blast
    caster.spell_slots = {3: 2}

    spell_hit_results = cast_spell(caster, primary, _fireball(), combat_state)

    assert {r.target for r in spell_hit_results} == {primary, bystander}

def test_aoe_spell_does_not_hit_targets_outside_the_radius(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player(level = 5)
    primary = _make_monster(name = "Primary", ac = 5)
    far_away = _make_monster(name = "Far Away", ac = 5)
    combat_state = _combat_state(caster, primary, far_away)
    combat_state.grid.place(caster, 30, 0) # keep the caster itself out of their own blast
    combat_state.grid.place(far_away, 10, 0) # 50ft from primary, outside a 20ft-radius blast
    caster.spell_slots = {3: 2}

    spell_hit_results = cast_spell(caster, primary, _fireball(), combat_state)

    assert {r.target for r in spell_hit_results} == {primary}

def test_aoe_spell_ignores_dead_combatants_in_the_blast(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player(level = 5)
    primary = _make_monster(name = "Primary", ac = 5)
    corpse = _make_monster(name = "Corpse", ac = 5)
    corpse.hp = 0
    combat_state = _combat_state(caster, primary, corpse)
    combat_state.grid.place(caster, 30, 0) # keep the caster itself out of their own blast
    caster.spell_slots = {3: 2}

    spell_hit_results = cast_spell(caster, primary, _fireball(), combat_state)

    assert {r.target for r in spell_hit_results} == {primary}

def test_aoe_spell_consumes_only_one_spell_slot_regardless_of_targets_hit(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    caster = _make_player(level = 5)
    primary = _make_monster(name = "Primary", ac = 5)
    bystander_a = _make_monster(name = "Bystander A", ac = 5)
    bystander_b = _make_monster(name = "Bystander B", ac = 5)
    combat_state = _combat_state(caster, primary, bystander_a, bystander_b)
    combat_state.grid.place(caster, 30, 0) # keep the caster itself out of their own blast
    caster.spell_slots = {3: 2}

    spell_hit_results = cast_spell(caster, primary, _fireball(), combat_state)

    assert len(spell_hit_results) == 3 # confirms the blast really did catch multiple targets
    assert caster.spell_slots[3] == 1

def test_aoe_spell_rolls_damage_once_and_shares_it_across_targets(monkeypatch):
    from dice import damage_roll as real_damage_roll
    call_count = {"n": 0}
    def counting_damage_roll(*args, **kwargs):
        call_count["n"] += 1
        return real_damage_roll(*args, **kwargs)
    monkeypatch.setattr("actions.damage_roll", counting_damage_roll)
    monkeypatch.setattr("dice.random.randint", lambda a, b: 1) # force every save to fail, keep it simple

    caster = _make_player(level = 5)
    primary = _make_monster(name = "Primary", ac = 5)
    bystander = _make_monster(name = "Bystander", ac = 5)
    combat_state = _combat_state(caster, primary, bystander)
    combat_state.grid.place(caster, 30, 0) # keep the caster itself out of their own blast
    caster.spell_slots = {3: 2}

    spell_hit_results = cast_spell(caster, primary, _fireball(), combat_state)

    assert call_count["n"] == 1
    assert spell_hit_results[0].amount == spell_hit_results[1].amount

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

# --- observation data carried on spell results / attack helpers ---

def _save_spell(**overrides):
    defaults: dict[str, Any] = dict(
        name = "Test Save Spell", level = 1, target_type = TargetType.ENEMY, damage_type = DamageType.FIRE,
        damage_dice = 1, damage_sides = 6, range = 60, requires_attack_roll = False,
        save_allowed = True, save_attribute = Ability.DEXTERITY
    )
    defaults.update(overrides)
    return Spell(**defaults)

def _two_combatant_state(caster, target):
    grid = Grid(10, 10)
    grid.place(caster, 0, 0)
    grid.place(target, 1, 0)
    return CombatState(grid = grid, initiative_order = [caster, target])

def test_spell_result_reports_the_save_that_was_actually_rolled():
    from actions import resolve_spell_against_target

    caster = _make_player()
    target = _make_monster()
    combat_state = _two_combatant_state(caster, target)

    result = resolve_spell_against_target(caster, target, _save_spell(), combat_state)

    assert result.save_ability == Ability.DEXTERITY
    assert result.save_dc == caster.spell_save_dc
    assert result.save_succeeded in (True, False)

def test_spell_result_reports_no_save_observation_when_the_target_auto_fails():
    from actions import resolve_spell_against_target

    caster = _make_player()
    target = _make_monster()
    target.add_effect(Paralysed())
    combat_state = _two_combatant_state(caster, target)

    result = resolve_spell_against_target(caster, target, _save_spell(save_attribute = Ability.DEXTERITY), combat_state)

    assert result.save_succeeded is None

def test_attack_roll_spells_report_the_attack_bonus_and_save_only_spells_do_not():
    from actions import resolve_spell_against_target

    caster = _make_player()
    target = _make_monster()
    combat_state = _two_combatant_state(caster, target)

    attack_spell = resolve_spell_against_target(caster, target, _save_spell(requires_attack_roll = True, save_allowed = False), combat_state)
    save_spell = resolve_spell_against_target(caster, target, _save_spell(), combat_state)

    assert attack_spell.attack_roll_bonus == caster.get_spell_attack_bonus()
    assert save_spell.attack_roll_bonus is None

def test_attack_roll_bonus_observed_is_none_for_an_automatic_melee_crit():
    from actions import attack_roll_bonus_observed

    attacker = _make_player()
    target = _make_monster()
    weapon = MeleeWeapon(name = "Sword", damage_dice = 1, damage_sides = 6, damage_type = DamageType.SLASHING, reach = 5, finesse = False)

    assert attack_roll_bonus_observed(attacker, target, weapon) == attacker.get_attack_bonus(weapon)

    target.add_effect(Paralysed())
    assert attack_roll_bonus_observed(attacker, target, weapon) is None


# --- spell damage follows RAW: no caster bonus unless the spell has its own ---

def _bonus_test_spell(**overrides):
    defaults: dict[str, Any] = dict(
        name = "Test Spell", level = 1, target_type = TargetType.ENEMY, damage_type = DamageType.FORCE,
        damage_dice = 3, damage_sides = 4, range = 120, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    defaults.update(overrides)
    return Spell(**defaults)

def test_a_damage_spell_adds_no_caster_bonus_to_its_damage(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 2)
    caster = _make_player(ability_scores = AbilityScores(intelligence = 18))
    caster.spell_slots = {1: 1}
    target = _make_monster()
    combat_state = _combat_state(caster, target)

    result = cast_spell(caster, target, _bonus_test_spell(), combat_state)[0]

    assert result.amount == 3 * 2 # a +7 spell attack bonus must not leak into damage

def test_a_spell_with_a_flat_damage_bonus_adds_exactly_that_bonus(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 2)
    caster = _make_player()
    caster.spell_slots = {1: 1}
    target = _make_monster()
    combat_state = _combat_state(caster, target)

    result = cast_spell(caster, target, _bonus_test_spell(damage_bonus = 3), combat_state)[0]

    assert result.amount == 3 * 2 + 3 # Magic Missile: three darts of 1d4 + 1

def test_a_healing_spell_adds_the_spellcasting_modifier(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 5)
    cleric = _make_player(ability_scores = AbilityScores(wisdom = 16), spellcasting_ability = Ability.WISDOM)
    cleric.spell_slots = {1: 1}
    ally = _make_player(name = "Ally")
    ally.hp = 1
    combat_state = _combat_state(cleric, ally)
    cure = _bonus_test_spell(name = "Cure Wounds", target_type = TargetType.ALLY, damage_type = None, is_healing = True, damage_dice = 1, damage_sides = 8, range = 5)

    result = cast_spell(cleric, ally, cure, combat_state)[0]

    assert result.amount == 5 + 3 # 1d8 + WIS modifier (+3), not the +6 spell attack bonus

def test_a_multi_ray_spell_makes_one_attack_roll_per_ray_for_a_single_slot(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 3)
    caster = _make_player()
    caster.spell_slots = {2: 1}
    target = _make_monster(ac = 1) # everything hits
    combat_state = _combat_state(caster, target)
    rays = _bonus_test_spell(name = "Scorching Ray", level = 2, damage_dice = 2, damage_sides = 6, requires_attack_roll = True, ray_count = 3)

    results = cast_spell(caster, target, rays, combat_state)

    assert len(results) == 3
    assert all(r.attack_roll_bonus == caster.get_spell_attack_bonus() for r in results)
    assert sum(r.amount for r in results) == 3 * (2 * 3)
    assert caster.spell_slots[2] == 0 # one slot, not three

def test_a_single_ray_spell_still_makes_exactly_one_attack(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 3)
    caster = _make_player()
    target = _make_monster(ac = 1)
    combat_state = _combat_state(caster, target)
    bolt = _bonus_test_spell(name = "Test Bolt", level = 0, damage_dice = 1, damage_sides = 10, requires_attack_roll = True)

    assert len(cast_spell(caster, target, bolt, combat_state)) == 1
