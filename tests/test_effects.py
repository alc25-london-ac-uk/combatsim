from typing import Any

from combatant import PlayerCharacter, AbilityScores
from effects import Barkskin, Blind, Concentrating, Effect, Frightened, Paralysed, Prone, Stunned, Unconscious
from dice import RollContext
from enums import Ability, RollType, DamageType
from weapon import MeleeWeapon, RangedWeapon

def _make_player(**overrides):
    defaults: dict[str, Any] = dict(
        name = "Test",
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

def _melee_weapon():
    return MeleeWeapon(name = "Test Sword", damage_dice = 1, damage_sides = 6, damage_type = DamageType.SLASHING, reach = 5, finesse = False)

def _ranged_weapon():
    return RangedWeapon(name = "Test Bow", damage_dice = 1, damage_sides = 6, damage_type = DamageType.PIERCING, optimal_distance = 80, maximum_distance = 320)

# --- duration / tick / expiry ---

def test_effect_with_no_duration_never_expires():
    effect = Effect(duration = None)
    for _ in range(100):
        effect.tick()
    assert effect.expired is False

def test_effect_expires_once_duration_reaches_zero():
    effect = Blind(duration = 2)
    assert effect.expired is False
    effect.tick()
    assert effect.expired is False
    effect.tick()
    assert effect.expired is True

def test_expired_effect_is_pruned_by_end_turn():
    target = _make_player()
    target.add_effect(Blind())
    for _ in range(9):
        target.end_turn()
        assert target.has_effect(Blind)
    target.end_turn()
    assert not target.has_effect(Blind)

def test_barkskin_and_paralysed_have_a_real_starting_duration():
    assert Barkskin().duration == 10
    assert Paralysed().duration == 10

# --- auto_fails_save ---

def test_paralysed_auto_fails_strength_and_dexterity_saves():
    effect = Paralysed()
    assert effect.auto_fails_save(Ability.STRENGTH) is True
    assert effect.auto_fails_save(Ability.DEXTERITY) is True

def test_paralysed_does_not_auto_fail_its_own_escape_save():
    effect = Paralysed()
    assert effect.auto_fails_save(Ability.WISDOM) is False

def test_stunned_and_unconscious_also_auto_fail_strength_and_dexterity_saves():
    assert Stunned().auto_fails_save(Ability.STRENGTH) is True
    assert Unconscious().auto_fails_save(Ability.DEXTERITY) is True

# --- auto_crit_in_melee ---

def test_paralysed_and_unconscious_grant_auto_crit_in_melee():
    assert Paralysed().auto_crit_in_melee is True
    assert Unconscious().auto_crit_in_melee is True

def test_stunned_does_not_grant_auto_crit_in_melee():
    assert Stunned().auto_crit_in_melee is False

# --- advantage / disadvantage: Blind ---

def test_blind_gives_itself_disadvantage_on_its_own_attacks():
    ctx = RollContext(RollType.ATTACK, is_roller = True)
    blind = Blind()
    assert blind.grants_disadvantage(ctx) is True
    assert blind.grants_advantage(ctx) is False

def test_blind_gives_advantage_to_attackers_targeting_it():
    ctx = RollContext(RollType.ATTACK, is_roller = False)
    blind = Blind()
    assert blind.grants_advantage(ctx) is True
    assert blind.grants_disadvantage(ctx) is False

def test_blind_does_not_affect_saving_throws():
    blind = Blind()
    for is_roller in (True, False):
        ctx = RollContext(RollType.SAVE, is_roller = is_roller)
        assert blind.grants_advantage(ctx) is False
        assert blind.grants_disadvantage(ctx) is False

# --- advantage / disadvantage: Prone (the melee/ranged split) ---

def test_prone_creature_has_disadvantage_on_its_own_attacks_regardless_of_weapon():
    prone = Prone()
    melee_ctx = RollContext(RollType.ATTACK, is_roller = True, weapon = _melee_weapon())
    ranged_ctx = RollContext(RollType.ATTACK, is_roller = True, weapon = _ranged_weapon())
    assert prone.grants_disadvantage(melee_ctx) is True
    assert prone.grants_disadvantage(ranged_ctx) is True

def test_melee_attacks_against_a_prone_target_have_advantage():
    prone = Prone()
    ctx = RollContext(RollType.ATTACK, is_roller = False, weapon = _melee_weapon())
    assert prone.grants_advantage(ctx) is True
    assert prone.grants_disadvantage(ctx) is False

def test_ranged_attacks_against_a_prone_target_have_disadvantage():
    prone = Prone()
    ctx = RollContext(RollType.ATTACK, is_roller = False, weapon = _ranged_weapon())
    assert prone.grants_disadvantage(ctx) is True
    assert prone.grants_advantage(ctx) is False

# --- Frightened: forbids_approaching ---

def test_frightened_only_forbids_approaching_its_own_source():
    source = _make_player(name = "Source")
    someone_else = _make_player(name = "Someone Else")
    frightened = Frightened(source = source)

    assert frightened.forbids_approaching(source) is True
    assert frightened.forbids_approaching(someone_else) is False

# --- Concentrating: ending it cascades to the maintained effect ---

def test_ending_concentration_removes_the_maintained_effect():
    caster = _make_player(name = "Caster")
    target = _make_player(name = "Target")

    maintained = Barkskin()
    target.add_effect(maintained)

    concentrating = Concentrating(maintained_effect = maintained, maintained_target = target)
    caster.add_effect(concentrating)

    caster.remove_effect(concentrating)

    assert not target.has_effect(Barkskin)

def test_unrelated_effect_removal_does_not_touch_concentration():
    caster = _make_player(name = "Caster")
    target = _make_player(name = "Target")

    maintained = Barkskin()
    target.add_effect(maintained)
    caster.add_effect(Concentrating(maintained_effect = maintained, maintained_target = target))

    caster.add_effect(Blind())
    caster.remove_effect(next(e for e in caster.effects if isinstance(e, Blind)))

    assert caster.has_effect(Concentrating)
    assert target.has_effect(Barkskin)
