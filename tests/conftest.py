from typing import Any

import pytest

from combatant import PlayerCharacter, Monster, AbilityScores
from weapon import MeleeWeapon, RangedWeapon
from enums import DamageType
from world import Grid, CombatState
from ai import CombatantAI

# Shared factories for building lightweight, real domain objects for tests.
# Each fixture returns a function so individual tests can still override whichever fields matter to them.

@pytest.fixture
def make_player():
    def _make(**overrides):
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
        player.ai = CombatantAI(player)
        return player
    return _make

@pytest.fixture
def make_monster():
    def _make(**overrides):
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
        monster.ai = CombatantAI(monster)
        return monster
    return _make

@pytest.fixture
def melee_weapon():
    def _make(**overrides):
        defaults: dict[str, Any] = dict(
            name = "Test Sword",
            damage_dice = 1,
            damage_sides = 6,
            damage_type = DamageType.SLASHING,
            reach = 5,
            finesse = False
        )
        defaults.update(overrides)
        return MeleeWeapon(**defaults)
    return _make

@pytest.fixture
def ranged_weapon():
    def _make(**overrides):
        defaults: dict[str, Any] = dict(
            name = "Test Bow",
            damage_dice = 1,
            damage_sides = 6,
            damage_type = DamageType.PIERCING,
            optimal_distance = 80,
            maximum_distance = 320
        )
        defaults.update(overrides)
        return RangedWeapon(**defaults)
    return _make

@pytest.fixture
def make_combat_state():
    def _make(*combatants):
        grid = Grid(10, 10)
        for c in combatants:
            grid.place(c, 0, 0)
        return CombatState(grid = grid, initiative_order = list(combatants))
    return _make