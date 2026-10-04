import json
import copy
from typing import Optional

from enums import TargetType, DamageType
from combatant import Combatant, PlayerCharacter, Monster, AbilityScores, Weapon, MeleeWeapon, RangedWeapon, Spell, Ability
from effects import Effect, EFFECT_REGISTRY, AcidArrow, Barkskin, Blind, Concentrating, Paralysed
from ai import CombatantAI
from policy import Policy
from ai_profile import CreatureAIProfile

def load_weapons(filepath: str) -> dict[str, Weapon]:
    with open(filepath) as f:
        data = json.load(f)
    
    weapons = {}
    for entry in data:
        try:
            weapon = parse_weapon(entry)
            weapons[entry["id"]] = weapon # creatures refer to a weapon by id; its name is only what is displayed
        except (KeyError, ValueError):
            print(f"Skipping {entry.get('id', 'unknown')}")
    
    return weapons

def load_spells(filepath: str) -> dict[str, Spell]:
    with open(filepath) as f:
        data = json.load(f)
    
    spells = {}
    for entry in data:
        try:
            spell = parse_spell(entry)
            spells[entry["name"]] = spell
        except (KeyError, ValueError) as e:
            print(f"Skipping {entry.get('name', 'unknown')}: {e}")

    return spells

def load_monsters(filepath: str, weapon_registry: dict[str, Weapon], spell_registry: dict[str, Spell]) -> dict[str, Combatant]:
    with open(filepath) as f:
        data = json.load(f)
    
    monsters = {}
    for entry in data:
        try:
            monster = parse_monster(entry, weapon_registry, spell_registry)
            monsters[entry["name"]] = monster
        except (KeyError, ValueError):
            print(f"Skipping {entry.get('name', 'unknown')}")
    
    return monsters

def load_players(filepath: str, weapon_registry: dict[str, Weapon], spell_registry: dict[str, Spell]) -> dict[str, Combatant]:
    with open(filepath) as f:
        data = json.load(f)
    
    player_characters = {}
    for entry in data:
        try:
            player_character = parse_player_character(entry, weapon_registry, spell_registry)
            player_characters[entry["name"]] = player_character
        except (KeyError, ValueError):
            print(f"Skipping {entry.get('name', 'unknown')}")
    
    return player_characters

def parse_weapon(entry: dict) -> Weapon:
    if entry["range"] == "melee":
        return MeleeWeapon(
            name = entry["name"],
            damage_dice = entry["damage_dice"],
            damage_sides = entry["damage_sides"],
            damage_type = DamageType[entry["damage_type"]],
            reach = entry["reach"],
            finesse = entry["finesse"]
        )
    else:
        return RangedWeapon(
            name = entry["name"],
            damage_dice = entry["damage_dice"],
            damage_sides = entry["damage_sides"],
            damage_type = DamageType[entry["damage_type"]],
            optimal_distance = entry["optimal_distance"],
            maximum_distance = entry["maximum_distance"],
            thrown = entry.get("thrown", False)
        )

def parse_spell(entry: dict) -> Spell:
    effect_name = entry.get("effect")
    effect_class = EFFECT_REGISTRY.get(effect_name) if effect_name else None

    return Spell(
        name = entry["name"],
        level = entry["level"],
        damage_type = DamageType[entry["damage_type"]] if entry.get("damage_type") else None,
        damage_dice = entry.get("damage_dice", 0),
        damage_sides = entry.get("damage_sides", 0),
        effect = effect_class,
        range = entry["range"],
        aoe_radius = entry.get("aoe_radius", 0),
        requires_attack_roll = entry["requires_attack_roll"],
        save_allowed = entry["save_allowed"],
        save_attribute = Ability(entry.get("save_attribute", "dexterity")),
        damage_dice_on_miss = entry.get("damage_dice_on_miss", 0.0),
        damage_pct_on_save = entry.get("damage_pct_on_save", 0.0),
        concentration = entry["concentration"],
        upcastable_extra_damage_die = entry.get("upcastable_extra_damage_die", False),
        upcastable_extra_target = entry.get("upcastable_extra_target", False),
        target_type = TargetType(entry.get("target_type")) if entry.get("target_type") else None,
        is_healing = entry.get("is_healing", False),
        is_bonus_action = entry.get("is_bonus_action", False),
        damage_bonus = entry.get("damage_bonus", 0),
        ray_count = entry.get("ray_count", 1)
    )

def parse_monster(entry: dict, weapon_registry: dict[str, Weapon], spell_registry: dict[str, Spell]) -> Monster:
    weapons = []
    weapon_attack_bonuses = {}
    for w in entry.get("weapons", []):
        weapon = copy.deepcopy(weapon_registry[w["id"]])
        if isinstance(weapon, MeleeWeapon):
            weapon.is_off_hand = w.get("is_off_hand", False)
        weapons.append(weapon)
        if "attack_bonus" in w:
            weapon_attack_bonuses[weapon.name] = w["attack_bonus"]

    spells = [spell_registry[name] for name in entry.get("spells", [])]

    return Monster(
        name = entry["name"],
        max_hp = entry["hit_points"],
        ac = entry["armor_class"],
        ability_scores = AbilityScores(
            strength = entry["strength"],
            dexterity = entry["dexterity"],
            constitution = entry["constitution"],
            intelligence = entry["intelligence"],
            wisdom = entry["wisdom"],
            charisma = entry["charisma"]
        ),
        speed = entry["speed"], # a flyer records its fly speed
        attack_count = entry["attack_count"],
        attack_bonus = entry["attack_bonus"],
        weapon_attack_bonuses = weapon_attack_bonuses,
        spell_bonus = entry.get("spell_bonus", 0),
        spellcaster_level = entry.get("spellcaster_level", 0),
        spellcasting_ability = Ability(entry.get("spellcasting_ability", "intelligence")),
        spell_slots = {int(k): v for k, v in entry.get("spell_slots", {}).items()},
        challenge_rating = entry["challenge_rating"],
        weapons = weapons,
        spells = spells,
        damage_vulnerabilities = [DamageType[v] for v in entry.get("damage_vulnerabilities", [])],
        damage_resistances = [DamageType[v] for v in entry.get("damage_resistances", [])],
        damage_immunities = [DamageType[v] for v in entry.get("damage_immunities", [])],
        can_fly = entry.get("can_fly", False)
    )

def parse_player_character(entry: dict, weapon_registry: dict[str, Weapon], spell_registry: dict[str, Spell]) -> PlayerCharacter:
    weapons = []
    for w in entry.get("weapons", []):
        weapon = copy.deepcopy(weapon_registry[w["id"]])
        if isinstance(weapon, MeleeWeapon):
            weapon.is_off_hand = w.get("is_off_hand", False)
        weapons.append(weapon)
        
    spells = [spell_registry[name] for name in entry.get("spells", [])]

    return PlayerCharacter(
        name = entry["name"],
        character_class = entry["character_class"],
        level = entry["level"],
        ac = entry["armor_class"],
        ability_scores = AbilityScores(
            strength = entry["strength"],
            dexterity = entry["dexterity"],
            constitution = entry["constitution"],
            intelligence = entry["intelligence"],
            wisdom = entry["wisdom"],
            charisma = entry["charisma"]
        ),
        spellcasting_ability = Ability(entry.get("spellcasting_ability", "intelligence")),
        spell_slots = {int(k): v for k, v in entry.get("spell_slots", {}).items()},
        weapons = weapons,
        spells = spells
    )

def spawn(registry: dict[str, Combatant], name: str, label: str = "", policy: Optional[Policy] = None, profile: Optional[CreatureAIProfile] = None) -> Combatant:
    combatant = copy.deepcopy(registry[name])
    combatant.name = label or name
    combatant.type_name = name
    combatant.ai = CombatantAI(combatant)
    if policy is not None:
        combatant.ai.policy = policy
    if profile is not None:
        combatant.ai.profile = profile
    return combatant