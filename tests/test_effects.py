from typing import Any

import pytest

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


# --- effects must never leave permanent changes behind (AC drift regression) ---

def test_removing_the_same_effect_twice_only_undoes_it_once(make_player):
    from effects import ShieldOfFaith

    ally = make_player(ac = 15)
    effect = ShieldOfFaith()
    ally.add_effect(effect)

    ally.remove_effect(effect)
    ally.remove_effect(effect)

    assert ally.ac == 15

def test_removing_an_effect_that_was_never_applied_changes_nothing(make_player):
    from effects import ShieldOfFaith

    ally = make_player(ac = 15)

    ally.remove_effect(ShieldOfFaith())

    assert ally.ac == 15

def test_a_broken_concentration_removes_the_maintained_buff_exactly_once(make_player):
    from effects import ShieldOfFaith, Concentrating

    caster = make_player(name = "Caster")
    ally = make_player(name = "Ally", ac = 15)
    shield = ShieldOfFaith()
    ally.add_effect(shield)
    concentration = Concentrating(maintained_effect = shield, maintained_target = ally)
    caster.add_effect(concentration)

    # the exact sequence Concentrating.on_damage_taken runs when the save is failed
    caster.remove_effect(concentration)
    ally.remove_effect(shield)

    assert ally.ac == 15

@pytest.mark.parametrize("shield_added_first", [True, False])
@pytest.mark.parametrize("shield_removed_first", [True, False])
def test_shield_of_faith_and_barkskin_leave_armour_class_unchanged_in_every_order(make_player, shield_added_first, shield_removed_first):
    # regression: Barkskin used to restore a saved absolute AC, so a Shield of Faith added or removed in between left a permanent +2 or -2
    from effects import ShieldOfFaith

    target = make_player(ac = 13)
    shield, barkskin = ShieldOfFaith(), Barkskin()

    for effect in ([shield, barkskin] if shield_added_first else [barkskin, shield]):
        target.add_effect(effect)
    for effect in ([shield, barkskin] if shield_removed_first else [barkskin, shield]):
        target.remove_effect(effect)

    assert target.ac == 13

@pytest.mark.parametrize("shield_added_first", [True, False])
def test_barkskin_is_a_floor_of_16_that_a_smaller_shield_of_faith_bonus_does_not_add_to(make_player, shield_added_first):
    from effects import ShieldOfFaith

    target = make_player(ac = 13) # 13 + 2 is still below the floor of 16
    effects = [ShieldOfFaith(), Barkskin()]
    for effect in (effects if shield_added_first else reversed(effects)):
        target.add_effect(effect)

    assert target.ac == 16

def test_shield_of_faith_still_adds_to_an_armour_class_already_above_the_barkskin_floor(make_player):
    from effects import ShieldOfFaith

    target = make_player(ac = 15)
    target.add_effect(Barkskin())
    target.add_effect(ShieldOfFaith())

    assert target.ac == 17

def test_ending_barkskin_while_shield_of_faith_lasts_leaves_the_shield_bonus(make_player):
    from effects import ShieldOfFaith

    target = make_player(ac = 13)
    barkskin = Barkskin()
    target.add_effect(ShieldOfFaith())
    target.add_effect(barkskin)
    target.remove_effect(barkskin)

    assert target.ac == 15

def test_barkskin_does_nothing_for_a_creature_already_at_or_above_16(make_player):
    target = make_player(ac = 18)
    barkskin = Barkskin()

    target.add_effect(barkskin)
    assert target.ac == 18

    target.remove_effect(barkskin)
    assert target.ac == 18

def test_the_armour_class_a_buff_would_add_accounts_for_what_the_target_already_has(make_player):
    from effects import ShieldOfFaith

    plain, barkskinned = make_player(ac = 13), make_player(ac = 13)
    barkskinned.add_effect(Barkskin()) # already at the floor of 16

    assert ShieldOfFaith().ac_gain(plain) == 2
    assert Barkskin().ac_gain(plain) == 3
    assert Barkskin().ac_gain(barkskinned) == 0

def test_resetting_combatants_after_a_fight_restores_every_armour_class(make_player):
    from effects import ShieldOfFaith, Concentrating

    caster = make_player(name = "Caster")
    ally = make_player(name = "Ally", ac = 15)
    shield = ShieldOfFaith()
    ally.add_effect(shield)
    caster.add_effect(Concentrating(maintained_effect = shield, maintained_target = ally))

    for combatant in (caster, ally):
        combatant.reset()

    assert ally.ac == 15 and caster.ac == 15
