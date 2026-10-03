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

    assert priest.spell_slots == {1: 4, 3: 2} # only levels with a spell the engine can model
    assert priest.max_spell_slots == {1: 4, 3: 2}

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


# --- the Wizard's spell list follows the 5th-level rules (9 prepared + 4 cantrips) ---

def test_the_wizard_knows_four_cantrips_and_prepares_nine_spells(player_registry):
    wizard = player_registry["Wizard"]
    cantrips = [s for s in wizard.spells if s.is_cantrip]
    prepared = [s for s in wizard.spells if not s.is_cantrip]

    assert len(cantrips) == 4 # 4 cantrips known at level 4+
    assert len(prepared) == 4 + 5 # INT modifier (+4 at INT 18) + wizard level

def test_the_wizards_prepared_spells_are_castable_with_his_slots(player_registry):
    wizard = player_registry["Wizard"]

    for spell in wizard.spells:
        assert spell.is_cantrip or wizard.spell_slots.get(spell.level, 0) > 0

def test_the_wizards_spell_list_matches_the_chosen_srd_spells(player_registry):
    names = {s.name for s in player_registry["Wizard"].spells}

    assert names == {
        "Fire Bolt", "Ray of Frost", "Shocking Grasp", "Poison Spray",
        "Magic Missile", "Thunderwave",
        "Acid Arrow", "Shatter", "Scorching Ray", "Hold Person",
        "Fireball", "Vampiric Touch", "Glyph of Warding",
    }

def test_srd_spell_values_are_loaded_as_written(spell_registry):
    assert (spell_registry["Magic Missile"].damage_dice, spell_registry["Magic Missile"].damage_sides, spell_registry["Magic Missile"].damage_bonus) == (3, 4, 3)
    assert spell_registry["Scorching Ray"].ray_count == 3 and spell_registry["Scorching Ray"].damage_dice == 2
    assert spell_registry["Shatter"].aoe_radius == 10 and spell_registry["Shatter"].damage_type == DamageType.THUNDER
    assert spell_registry["Thunderwave"].damage_dice == 2 and spell_registry["Thunderwave"].damage_sides == 8
    assert spell_registry["Glyph of Warding"].damage_type == DamageType.COLD and spell_registry["Glyph of Warding"].aoe_radius == 20
    assert spell_registry["Vampiric Touch"].range == 5
    assert spell_registry["Poison Spray"].range == 10 and spell_registry["Poison Spray"].save_attribute.value == "constitution"

def test_monster_casters_use_their_own_spellcasting_ability(monster_registry):
    assert monster_registry["Priest"].spellcasting_ability.value == "wisdom"
    assert monster_registry["Mage"].spellcasting_ability.value == "intelligence"

# --- the Cleric's spell list ---

def test_the_cleric_knows_only_sacred_flame_as_a_cantrip(player_registry):
    cantrips = [s.name for s in player_registry["Cleric"].spells if s.is_cantrip]

    assert cantrips == ["Sacred Flame"]

def test_the_cleric_does_not_have_a_non_cleric_spell(player_registry):
    assert "Barkskin" not in {s.name for s in player_registry["Cleric"].spells}

def test_spirit_guardians_is_a_radius_burst_of_6d8_radiant_with_a_wisdom_save(spell_registry):
    spirit_guardians = spell_registry["Spirit Guardians"]

    assert (spirit_guardians.damage_dice, spirit_guardians.damage_sides) == (6, 8)
    assert spirit_guardians.damage_type == DamageType.RADIANT
    assert spirit_guardians.aoe_radius == 15
    assert spirit_guardians.save_attribute.value == "wisdom"
    assert spirit_guardians.damage_pct_on_save == 0.5
    assert spirit_guardians.concentration is False # an instant burst has no ongoing effect to concentrate on

def test_guiding_bolt_is_a_4d6_radiant_ranged_spell_attack(spell_registry):
    guiding_bolt = spell_registry["Guiding Bolt"]

    assert (guiding_bolt.level, guiding_bolt.damage_dice, guiding_bolt.damage_sides, guiding_bolt.range) == (1, 4, 6, 120)
    assert guiding_bolt.requires_attack_roll is True


# --- Shield of Faith, buff valuation, and the Fighter's Longbow ---

def test_shield_of_faith_adds_two_ac_while_active_and_restores_it(make_player):
    from effects import ShieldOfFaith

    ally = make_player(ac = 15)
    effect = ShieldOfFaith()

    ally.add_effect(effect)
    assert ally.ac == 17

    ally.remove_effect(effect)
    assert ally.ac == 15

def test_shield_of_faith_is_registered_as_an_effect_the_spell_data_can_name():
    from effects import EFFECT_REGISTRY, ShieldOfFaith

    assert EFFECT_REGISTRY["Shield of Faith"] is ShieldOfFaith

def test_the_cleric_prepares_eight_spells_and_one_cantrip(player_registry):
    cleric = player_registry["Cleric"]

    assert len([s for s in cleric.spells if s.is_cantrip]) == 1
    assert len([s for s in cleric.spells if not s.is_cantrip]) == 3 + 5 # WIS modifier + cleric level
    assert {s.name for s in cleric.spells} == {
        "Sacred Flame",
        "Cure Wounds", "Healing Word", "Guiding Bolt", "Inflict Wounds", "Shield of Faith",
        "Hold Person", "Blindness",
        "Spirit Guardians",
    }

def test_shield_of_faith_loads_as_a_concentration_bonus_action_ally_buff(spell_registry):
    from effects import ShieldOfFaith

    spell = spell_registry["Shield of Faith"]

    assert spell.effect is ShieldOfFaith
    assert spell.is_bonus_action is True
    assert spell.concentration is True
    assert spell.target_type == TargetType.ALLY

def test_the_fighter_carries_a_melee_weapon_and_a_longbow(player_registry):
    from weapon import MeleeWeapon, RangedWeapon

    fighter = player_registry["Fighter"]

    assert any(isinstance(w, MeleeWeapon) for w in fighter.weapons)
    longbows = [w for w in fighter.weapons if w.name == "Longbow"]
    assert len(longbows) == 1 and isinstance(longbows[0], RangedWeapon)


# --- SRD monster pool for belief testing ---

def test_monster_casters_carry_only_their_srd_spells_that_the_engine_can_model(monster_registry):
    names = lambda monster: {s.name for s in monster.spells}

    assert names(monster_registry["Priest"]) == {"Sacred Flame", "Cure Wounds", "Guiding Bolt", "Spirit Guardians"}
    assert names(monster_registry["Mage"]) == {"Fire Bolt", "Magic Missile", "Fireball"}
    assert names(monster_registry["Cult Fanatic"]) == {"Sacred Flame", "Inflict Wounds", "Shield of Faith", "Hold Person"}
    assert names(monster_registry["Druid"]) == {"Produce Flame", "Thunderwave", "Barkskin"}
    assert names(monster_registry["Acolyte"]) == {"Sacred Flame", "Cure Wounds"}

def test_no_monster_caster_has_slots_at_a_level_where_it_has_no_modelled_spell(monster_registry):
    for monster in monster_registry.values():
        if not monster.spells:
            continue
        spell_levels = {s.level for s in monster.spells}
        for level, slots in monster.spell_slots.items():
            if slots > 0:
                assert level in spell_levels, f"{monster.name} has level {level} slots but no level {level} spell"

def test_the_new_srd_monsters_have_their_published_damage_modifiers(monster_registry):
    assert DamageType.BLUDGEONING in monster_registry["Warhorse Skeleton"].damage_vulnerabilities
    assert DamageType.BLUDGEONING in monster_registry["Minotaur Skeleton"].damage_vulnerabilities
    assert DamageType.THUNDER in monster_registry["Earth Elemental"].damage_vulnerabilities
    assert set(monster_registry["Earth Elemental"].damage_resistances) == {DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING}
    assert set(monster_registry["Xorn"].damage_resistances) == {DamageType.PIERCING, DamageType.SLASHING} # bludgeoning still works
    assert DamageType.NECROTIC in monster_registry["Wight"].damage_resistances
    assert set(monster_registry["Dretch"].damage_resistances) == {DamageType.COLD, DamageType.FIRE, DamageType.LIGHTNING}
    assert DamageType.COLD in monster_registry["Salamander"].damage_vulnerabilities
    assert DamageType.FIRE in monster_registry["Salamander"].damage_immunities
    assert DamageType.POISON in monster_registry["Ogre Zombie"].damage_immunities

def test_the_new_srd_monsters_match_their_published_core_stats(monster_registry):
    expected = {
        "Earth Elemental": (17, 126, 5), "Xorn": (19, 73, 5), "Wight": (14, 45, 3), "Cult Fanatic": (13, 33, 2),
        "Druid": (11, 27, 2), "Minotaur Skeleton": (12, 67, 2), "Warhorse Skeleton": (13, 22, 0.5),
        "Ogre Zombie": (8, 85, 2), "Grick": (14, 27, 2), "Dretch": (11, 18, 0.25), "Salamander": (15, 90, 5),
    }

    for name, (ac, hp, cr) in expected.items():
        monster = monster_registry[name]
        assert (monster.ac, monster.max_hp, monster.challenge_rating) == (ac, hp, cr), name

def test_monster_damage_bonuses_follow_from_their_ability_scores_as_published(monster_registry, weapon_registry):
    # the engine derives a weapon's flat damage bonus from the wielder's ability scores
    elemental = monster_registry["Earth Elemental"]
    assert elemental.get_damage_bonus(weapon_registry["Slam - Earth Elemental"]) == 5 # 2d8+5
    skeleton = monster_registry["Minotaur Skeleton"]
    assert skeleton.get_damage_bonus(weapon_registry["Greataxe - Minotaur Skeleton"]) == 4 # 2d12+4
    fanatic = monster_registry["Cult Fanatic"]
    assert fanatic.get_damage_bonus(weapon_registry["Dagger"]) == 2 # 1d4+2, finesse uses Dex

def test_the_xorns_blended_attack_averages_its_real_multiattack(weapon_registry):
    blended = weapon_registry["Claws and Bite - Xorn"]
    per_attack = blended.damage_dice * (blended.damage_sides + 1) / 2 + 3 # +3 from Str

    real_average = (3 * (1 * 3.5 + 3) + (3 * 3.5 + 3)) / 4 # three 1d6+3 claws and one 3d6+3 bite
    assert abs(per_attack - real_average) < 0.5

# --- named encounters ---

# --- reused combatants must not accumulate state across fights ---

def test_armour_class_does_not_drift_over_many_reused_fights(player_registry, monster_registry):
    import random
    from combat import run_combat
    from scenarios import build_party, build_encounter
    from policy_greedyutility import GreedyUtilityPolicy

    random.seed(0)
    party = build_party(player_registry, GreedyUtilityPolicy())
    enemies = build_encounter("five_casters_with_undead", monster_registry, GreedyUtilityPolicy()) # healers and concentration casters
    combatants = party + enemies
    original_ac = {c.name: c.ac for c in combatants}

    for _ in range(40):
        run_combat(party, enemies)
        for c in combatants:
            c.reset()
        assert {c.name: c.ac for c in combatants} == original_ac
