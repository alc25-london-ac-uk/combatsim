from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from enums import Ability, DamageType
from weapon import Weapon, MeleeWeapon, RangedWeapon
from spell import Spell
from effects import Effect

if TYPE_CHECKING:
    from ai import CombatantAI

@dataclass
class AbilityScores:
    strength:       int = 10
    dexterity:      int = 10
    constitution:   int = 10
    intelligence:   int = 10
    wisdom:         int = 10
    charisma:       int = 10

    def modifier(self, score) -> int:
        return (score - 10) // 2
    
    def modifier_for(self, ability: Ability) -> int:
        score = getattr(self, ability.value)
        return self.modifier(score)
    
    @property
    def str_mod(self) -> int: return self.modifier(self.strength)
    @property
    def dex_mod(self) -> int: return self.modifier(self.dexterity)
    @property
    def con_mod(self) -> int: return self.modifier(self.constitution)
    @property
    def int_mod(self) -> int: return self.modifier(self.intelligence)
    @property
    def wis_mod(self) -> int: return self.modifier(self.wisdom)
    @property
    def cha_mod(self) -> int: return self.modifier(self.charisma)

@dataclass(eq=False)
class Combatant(ABC):
    name: str
    ac: int
    ability_scores: AbilityScores
    weapons: list[Weapon] = field(default_factory = list)
    spells: list[Spell] = field(default_factory = list)
    effects: list[Effect] = field(default_factory = list)
    ai: Optional[CombatantAI] = field(default = None)
    speed: int = 30
    spellcasting_ability: Ability = Ability.INTELLIGENCE
    spell_slots: dict[int, int] = field(default_factory = dict)
    team: str = "unassigned"
    hp: int = 1
    movement: int = field(init = False)
    max_spell_slots: dict[int, int] = field(init = False, default_factory = dict)
    attack_count: int = 1
    has_action: bool = True
    has_bonus_action: bool = True
    has_reaction: bool = True
    damage_vulnerabilities: list[DamageType] = field(default_factory = list)
    damage_resistances: list[DamageType] = field(default_factory = list)
    damage_immunities: list[DamageType] = field(default_factory = list)
    can_fly: bool = False
    type_name: str = ""

    def __post_init__(self):
        self.movement = self.speed
        self.max_spell_slots = dict(self.spell_slots)
        self.base_ac = self.ac

    @property
    def alive(self) -> bool:
        return self.hp > 0
    
    def roll_initiative(self) -> int:
        return random.randint(1, 20) + self.ability_scores.dex_mod

    @property
    @abstractmethod
    def max_hp(self) -> int:
        pass

    @property
    @abstractmethod
    def caster_level(self) -> int:
        pass

    @property
    @abstractmethod
    def spell_save_dc(self) -> int:
        pass

    @abstractmethod
    def get_spell_attack_bonus(self) -> int:
        pass

    @abstractmethod
    def get_attack_bonus(self, weapon: Weapon) -> int:
        pass

    def get_damage_bonus(self, weapon: Weapon) -> int:
        if (isinstance(weapon, RangedWeapon) and not weapon.thrown) or (isinstance(weapon, MeleeWeapon) and weapon.finesse):
            return self.ability_scores.dex_mod
        else:
            return self.ability_scores.str_mod

    def reset(self) -> None:
        self.hp = self.max_hp
        self.movement = self.speed
        self.spell_slots = dict(self.max_spell_slots)

        self.has_action = True
        self.has_bonus_action = True
        self.has_reaction = True

        if self.ai is not None:
            self.ai.reset()

        for e in list(self.effects):
            self.remove_effect(e)
        self.ac = self.base_ac

    @property
    def is_immobilised(self) -> bool:
        return any(e.immobilises for e in self.effects)

    def start_turn(self) -> None:
        self.movement = 0 if self.is_immobilised else self.speed

        self.has_action = True
        self.has_bonus_action = True
        self.has_reaction = True

        for e in self.effects:
            e.on_turn_start(self)

    def end_turn(self) -> None:
        for e in self.effects:
            e.on_turn_end(self)
        for e in self.effects:
            e.tick()
        for e in list(self.effects):
            if e.expired:
                self.remove_effect(e)

    def has_effect(self, effect_type: type) -> bool:
        return any(isinstance(e, effect_type) for e in self.effects)

    def armour_class_with(self, effects: list[Effect]) -> int:
        armour_class = self.base_ac + sum(e.ac_bonus for e in effects)
        return max([armour_class] + [e.ac_floor for e in effects])

    def add_effect(self, effect: Effect) -> None:
        effect.on_apply(self)
        self.effects.append(effect)
        self.ac = self.armour_class_with(self.effects)

    def remove_effect(self, effect: Effect) -> None:
        if not any(e is effect for e in self.effects):
            return # removing an effect twice mustn't undo its on_remove side effects twice

        effect.on_remove(self)
        self.effects = [e for e in self.effects if e is not effect]
        self.ac = self.armour_class_with(self.effects)

    def take_damage(self, amount: int, damage_type: DamageType) -> int:
        if self.immune_to(damage_type):
            return 0

        if self.resistant_to(damage_type):
            amount = int(amount * 0.5)
        elif self.vulnerable_to(damage_type):
            amount *= 2

        self.hp -= amount
        for effect in self.effects:
            effect.on_damage_taken(self, amount)

        return amount

    def heal(self, amount: int) -> None:
        self.hp = min(self.hp + amount, self.max_hp)

    def immune_to(self, damage_type: DamageType) -> bool:
        return damage_type in self.damage_immunities

    def resistant_to(self, damage_type: DamageType) -> bool:
        return damage_type in self.damage_resistances

    def vulnerable_to(self, damage_type: DamageType) -> bool:
        return damage_type in self.damage_vulnerabilities

# TODO: Class features (e.g. turn undead)
@dataclass(eq=False)
class PlayerCharacter(Combatant):
    team: str = "party"
    level: int = 1
    character_class: str = "fighter"

    def __post_init__(self):
        super().__post_init__()
        self.attack_count = self._compute_attack_count()

    @property
    def max_hp(self) -> int:
        con_mod = self.ability_scores.con_mod
        match self.character_class:
            case "cleric" | "rogue":
                hit_dice = 8
            case "fighter":
                hit_dice = 10
            case "wizard":
                hit_dice = 6
        first_level = hit_dice + con_mod
        subsequent_levels = (hit_dice // 2 + 1 + con_mod) * (self.level - 1)
        return max(first_level + subsequent_levels, 1)

    @property
    def caster_level(self) -> int:
        return self.level

    def _compute_attack_count(self) -> int:
        match self.character_class:
            case "fighter":
                return 2 if self.level >= 5 else 1
            case _:
                return 1
    
    @property
    def proficiency_bonus(self) -> int:
        return 2 + (self.level - 1) // 4
    
    @property
    def spell_save_dc(self) -> int:
        return 8 + self.proficiency_bonus + self.ability_scores.modifier_for(self.spellcasting_ability)
    
    def get_spell_attack_bonus(self) -> int:
        return self.proficiency_bonus + self.ability_scores.modifier_for(self.spellcasting_ability)

    def get_attack_bonus(self, weapon: Weapon) -> int:
        if (isinstance(weapon, RangedWeapon) and not weapon.thrown) or (isinstance(weapon, MeleeWeapon) and weapon.finesse):
            return self.proficiency_bonus + self.ability_scores.dex_mod
        else:
            return self.proficiency_bonus + self.ability_scores.str_mod

# TODO: feats: Charge
# TODO: feats: Pack Tactics
@dataclass(eq=False)
class Monster(Combatant):
    team: str = "enemies"
    max_hp: int = 1
    attack_count: int = 1
    attack_bonus: int = 0
    weapon_attack_bonuses: dict[str, int] = field(default_factory = dict) # for a weapon whose to-hit differs from attack_bonus (e.g. a gnoll's longbow), by weapon name
    spell_bonus: int = 0
    spellcaster_level: int = 0
    challenge_rating: float = 0.0

    def get_attack_bonus(self, weapon: Weapon) -> int:
        return self.weapon_attack_bonuses.get(weapon.name, self.attack_bonus)

    @property
    def caster_level(self) -> int:
        return self.spellcaster_level
    
    @property
    def spell_save_dc(self) -> int:
        return 8 + self.spell_bonus
    
    def get_spell_attack_bonus(self) -> int:
        return self.spell_bonus