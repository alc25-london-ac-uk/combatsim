from pathlib import Path

import pytest

from data import load_weapons, load_spells, load_players, load_monsters
from scenarios import build_party
from cr_difficulty import (
    XP_BY_CR, XP_THRESHOLDS_BY_LEVEL, TIERS,
    encounter_multiplier, adjusted_encounter_xp, party_thresholds, classify_difficulty, print_named_encounter_difficulty,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

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

# --- encounter_multiplier ---

def test_encounter_multiplier_matches_the_dmg_table():
    assert encounter_multiplier(1) == 1.0
    assert encounter_multiplier(2) == 1.5
    assert encounter_multiplier(3) == 2.0
    assert encounter_multiplier(6) == 2.0
    assert encounter_multiplier(7) == 2.5
    assert encounter_multiplier(10) == 2.5
    assert encounter_multiplier(11) == 3.0
    assert encounter_multiplier(14) == 3.0
    assert encounter_multiplier(15) == 4.0
    assert encounter_multiplier(20) == 4.0

# --- classify_difficulty ---

def test_classify_difficulty_trivial_below_easy_threshold(player_registry, monster_registry):
    party = build_party(player_registry) # 4 level-5 PCs, easy threshold = 1000 total
    tier = classify_difficulty(["Goblin"], monster_registry, party) # CR 1/4 = 50 XP, x1 = 50

    assert tier == "Trivial"

def test_classify_difficulty_deadly_above_deadly_threshold(player_registry, monster_registry):
    party = build_party(player_registry) # deadly threshold = 4 * 1100 = 4400
    # 6 monsters at CR >= 2 (>= 450 XP each) = >= 2700 total, x2 multiplier = >= 5400 adjusted
    cr2_plus = next(name for name, m in monster_registry.items() if m.challenge_rating >= 2)
    tier = classify_difficulty([cr2_plus] * 6, monster_registry, party)

    assert tier == "Deadly"

def test_classify_difficulty_respects_party_level(player_registry, monster_registry):
    # same monsters, a lower-level party should see it as relatively harder
    low_level_party = build_party(player_registry)
    for p in low_level_party:
        p.level = 1

    high_level_party = build_party(player_registry)
    for p in high_level_party:
        p.level = 5

    goblin_squad = ["Goblin", "Goblin", "Goblin"]
    low_level_tier = classify_difficulty(goblin_squad, monster_registry, low_level_party)
    high_level_tier = classify_difficulty(goblin_squad, monster_registry, high_level_party)

    assert TIERS.index(low_level_tier) >= TIERS.index(high_level_tier)

# --- adjusted XP, thresholds and the printed table ---

def test_adjusted_encounter_xp_applies_the_size_multiplier(monster_registry):
    # three CR 1/4 goblins are 50 XP each, in the 3-6 monster band (x2)
    assert adjusted_encounter_xp(["Goblin", "Goblin", "Goblin"], monster_registry) == 3 * 50 * 2.0

def test_party_thresholds_sum_the_per_character_thresholds(player_registry):
    thresholds = party_thresholds(build_party(player_registry))

    assert thresholds == {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4400}

def test_the_printed_table_lists_every_named_encounter_with_a_tier(player_registry, monster_registry, capsys):
    from scenarios import ENCOUNTERS

    print_named_encounter_difficulty(monster_registry, build_party(player_registry))

    output = capsys.readouterr().out
    for name in ENCOUNTERS:
        assert name in output
    assert any(tier in output for tier in TIERS)
