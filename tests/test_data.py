import json
from pathlib import Path

import pytest

from data import load_weapons, load_spells, load_monsters, load_players, parse_player_character, parse_monster, spawn
from enums import DamageType, TargetType, TargetPriority
from weapon import MeleeWeapon
from policy_greedyutility import GreedyUtilityPolicy
from policy_beliefupdating import BeliefUpdatingPolicy
from ai_profile import CreatureAIProfile

REPO_ROOT = Path(__file__).resolve().parent.parent

def _load_json(filename):
    with open(REPO_ROOT / filename) as f:
        return json.load(f)

@pytest.fixture
def weapon_registry():
    return load_weapons(str(REPO_ROOT / "weapons.json"))

@pytest.fixture
def spell_registry():
    return load_spells(str(REPO_ROOT / "spells.json"))

@pytest.fixture
def monster_registry(weapon_registry, spell_registry):
    return load_monsters(str(REPO_ROOT / "monsters.json"), weapon_registry, spell_registry)

@pytest.fixture
def player_registry(weapon_registry, spell_registry):
    return load_players(str(REPO_ROOT / "players.json"), weapon_registry, spell_registry)

def test_all_weapons_parse_without_skipping(capsys, weapon_registry):
    assert "Skipping" not in capsys.readouterr().out
    assert len(weapon_registry) == len(_load_json("weapons.json"))

def test_all_spells_parse_without_skipping(capsys, spell_registry):
    assert "Skipping" not in capsys.readouterr().out
    assert len(spell_registry) == len(_load_json("spells.json"))

def test_all_monsters_parse_without_skipping(capsys, monster_registry):
    assert "Skipping" not in capsys.readouterr().out
    assert len(monster_registry) == len(_load_json("monsters.json"))

def test_all_players_parse_without_skipping(capsys, player_registry):
    assert "Skipping" not in capsys.readouterr().out
    assert len(player_registry) == len(_load_json("players.json"))

def test_weapon_damage_type_is_a_real_enum_member(weapon_registry):
    assert weapon_registry["Longsword"].damage_type == DamageType.SLASHING

def test_cure_wounds_is_flagged_as_healing_and_ally_targeted(spell_registry):
    cure_wounds = spell_registry["Cure Wounds"]
    assert cure_wounds.is_healing is True
    assert cure_wounds.target_type == TargetType.ALLY

def test_player_spell_slots_use_integer_levels_as_keys(player_registry):
    cleric = player_registry["Cleric"]
    assert cleric.spell_slots == {1: 4, 2: 3, 3: 2}
    assert all(isinstance(level, int) for level in cleric.spell_slots)

def test_monster_spellcaster_level_defaults_to_zero(monster_registry):
    assert monster_registry["Goblin"].spellcaster_level == 0

def test_duplicate_weapon_names_produce_independent_objects_for_players(weapon_registry, spell_registry):
    entry = {
        "name": "Test Dual Wielder",
        "character_class": "rogue",
        "level": 1,
        "armor_class": 12,
        "strength": 10, "dexterity": 16, "constitution": 12,
        "intelligence": 10, "wisdom": 10, "charisma": 10,
        "weapons": [
            {"name": "Scimitar", "is_off_hand": False},
            {"name": "Scimitar", "is_off_hand": True}
        ]
    }

    player = parse_player_character(entry, weapon_registry, spell_registry)
    first_weapon, second_weapon = player.weapons
    assert isinstance(first_weapon, MeleeWeapon)
    assert isinstance(second_weapon, MeleeWeapon)

    assert first_weapon is not second_weapon
    assert first_weapon.is_off_hand is False
    assert second_weapon.is_off_hand is True

# --- spawn() ---

def test_spawn_defaults_to_the_greedy_utility_policy(monster_registry):
    goblin = spawn(monster_registry, "Goblin")

    assert isinstance(goblin.ai.policy, GreedyUtilityPolicy)

def test_spawn_accepts_an_explicit_policy_override(monster_registry):
    goblin = spawn(monster_registry, "Goblin", policy = BeliefUpdatingPolicy())

    assert isinstance(goblin.ai.policy, BeliefUpdatingPolicy)

def test_spawn_gives_each_combatant_their_own_beliefs_dict(monster_registry):
    shared_policy = BeliefUpdatingPolicy()
    first = spawn(monster_registry, "Goblin", label = "A", policy = shared_policy)
    second = spawn(monster_registry, "Goblin", label = "B", policy = shared_policy)

    assert first.ai.policy is second.ai.policy # sharing one stateless policy instance is fine
    assert first.ai.beliefs is not second.ai.beliefs # but beliefs must never be shared

def test_spawn_defaults_to_a_creature_ai_profile_for_monsters(monster_registry):
    goblin = spawn(monster_registry, "Goblin")

    assert isinstance(goblin.ai.profile, CreatureAIProfile)

def test_spawn_accepts_an_explicit_profile_override(monster_registry):
    custom_profile = CreatureAIProfile(target_priority = TargetPriority.HIGHEST_THREAT)

    goblin = spawn(monster_registry, "Goblin", profile = custom_profile)

    assert goblin.ai.profile is custom_profile
    assert goblin.ai.profile.target_priority == TargetPriority.HIGHEST_THREAT

def test_duplicate_weapon_names_produce_independent_objects_for_monsters(weapon_registry, spell_registry):
    entry = {
        "name": "Test Dual Wielding Monster",
        "hit_points": 10,
        "armor_class": 12,
        "strength": 10, "dexterity": 16, "constitution": 12,
        "intelligence": 10, "wisdom": 10, "charisma": 10,
        "attack_count": 2,
        "attack_bonus": 3,
        "challenge_rating": 1,
        "weapons": [
            {"name": "Scimitar", "is_off_hand": False},
            {"name": "Scimitar", "is_off_hand": True}
        ]
    }

    monster = parse_monster(entry, weapon_registry, spell_registry)
    first_weapon, second_weapon = monster.weapons
    assert isinstance(first_weapon, MeleeWeapon)
    assert isinstance(second_weapon, MeleeWeapon)

    assert first_weapon is not second_weapon
    assert first_weapon.is_off_hand is False
    assert second_weapon.is_off_hand is True

# --- spell coverage ---

def test_every_caster_has_a_spell_for_every_slot_level_they_hold(player_registry):
    for player in player_registry.values():
        for level, slots in player.spell_slots.items():
            if slots > 0:
                assert any(s.level == level for s in player.spells), f"{player.name} has level {level} slots but no level {level} spell"

def test_every_spellcaster_with_slots_has_a_cantrip(player_registry):
    for player in player_registry.values():
        if any(slots > 0 for slots in player.spell_slots.values()):
            assert any(s.is_cantrip for s in player.spells), f"{player.name} has no cantrip fallback"

def test_healing_word_loads_as_a_bonus_action_heal(spell_registry):
    healing_word = spell_registry["Healing Word"]

    assert healing_word.is_bonus_action is True
    assert healing_word.is_healing is True

def test_only_flagged_spells_are_bonus_actions(spell_registry):
    assert spell_registry["Cure Wounds"].is_bonus_action is False
    assert spell_registry["Fireball"].is_bonus_action is False

# --- monster spellcasting and damage modifiers ---

def test_monster_spell_slots_use_integer_levels_as_keys(monster_registry):
    priest = monster_registry["Priest"]

    assert priest.spell_slots == {1: 4, 2: 3, 3: 2}
    assert priest.max_spell_slots == {1: 4, 2: 3, 3: 2}

def test_every_monster_spell_is_castable_with_its_slots(monster_registry):
    for monster in monster_registry.values():
        for spell in monster.spells:
            assert spell.is_cantrip or monster.spell_slots.get(spell.level, 0) > 0, f"{monster.name} cannot cast {spell.name}"

def test_new_monsters_expose_vulnerabilities_resistances_and_immunities(monster_registry):
    assert DamageType.BLUDGEONING in monster_registry["Skeleton"].damage_vulnerabilities
    assert DamageType.FIRE in monster_registry["Magmin"].damage_immunities
    assert DamageType.FIRE in monster_registry["Mummy"].damage_vulnerabilities
    assert DamageType.SLASHING in monster_registry["Gargoyle"].damage_resistances

def test_spawn_records_the_registry_name_as_the_creature_type_even_when_labelled(monster_registry):
    skeleton = spawn(monster_registry, "Skeleton", "Skeleton 3")

    assert skeleton.name == "Skeleton 3"
    assert skeleton.type_name == "Skeleton"
