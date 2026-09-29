from typing import Any

from spell import Spell
from enums import Ability, TargetType

def _make_spell(**overrides):
    defaults: dict[str, Any] = dict(
        name = "Test Spell",
        level = 1,
        target_type = TargetType.ENEMY,
        damage_type = None,
        damage_dice = 1,
        damage_sides = 6,
        range = 60,
        requires_attack_roll = False,
        save_allowed = False,
        save_attribute = Ability.DEXTERITY
    )
    defaults.update(overrides)
    return Spell(**defaults)

def test_level_zero_spell_is_a_cantrip():
    assert _make_spell(level = 0).is_cantrip is True

def test_level_one_and_above_spells_are_not_cantrips():
    assert _make_spell(level = 1).is_cantrip is False
    assert _make_spell(level = 3).is_cantrip is False

def test_optional_fields_default_sensibly():
    spell = _make_spell()
    assert spell.is_healing is False
    assert spell.is_bonus_action is False
    assert spell.concentration is False
    assert spell.effect is None
    assert spell.damage_dice_on_miss == 0
    assert spell.damage_pct_on_save == 0
    assert spell.upcastable_extra_damage_die is False
    assert spell.upcastable_extra_target is False
    assert spell.aoe_radius == 0
