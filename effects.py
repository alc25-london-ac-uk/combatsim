from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import random
from dataclasses import dataclass
from abc import ABC

from dice import saving_throw, RollContext, resolve_advantage
from enums import Ability, RollType, DamageType
from weapon import Weapon, MeleeWeapon, RangedWeapon

if TYPE_CHECKING:
    from combatant import Combatant

@dataclass
class Effect(ABC):
    name: str = ""
    source: Optional[Combatant] = None
    duration: Optional[int] = None
    save_dc: int = 0
    levels_upcast: int = 0
    prevent_turn: bool = False
    auto_crit_in_melee: bool = False

    def on_apply(self, target: Combatant) -> None:
        pass

    def on_remove(self, target: Combatant) -> None:
        pass

    def on_turn_start(self, target: Combatant) -> None:
        pass

    def on_turn_end(self, target: Combatant) -> None:
        pass

    def on_damage_taken(self, target: Combatant, amount: int) -> None:
        pass

    @property
    def expired(self) -> bool:
        return self.duration is not None and self.duration <= 0
    
    def tick(self) -> None:
        if self.duration is not None:
            self.duration -= 1

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return False

    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        return False

    def auto_fails_save(self, ability: Ability) -> bool:
        return False

    def forbids_approaching(self, other: Combatant) -> bool:
        return False

@dataclass
class AcidArrow(Effect):
    name: str = "Acid Arrow"

    def on_turn_end(self, target: Combatant) -> None:
        damage = 0
        for i in range(0,self.levels_upcast + 2):
            damage += random.randint(1, 4)
        target.take_damage(damage, DamageType.ACID)
        target.remove_effect(self)

@dataclass
class Barkskin(Effect):
    name: str = "Barkskin"
    previous_ac: int = 0
    duration: int = 10

    def on_apply(self, target: Combatant) -> None:
        self.previous_ac = target.ac

        if target.ac < 16:
            target.ac = 16

    def on_remove(self, target: Combatant) -> None:
        target.ac = self.previous_ac

@dataclass
class Blind(Effect):
    name: str = "Blind"
    duration: int = 10

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller

    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and roll_context.is_roller

@dataclass
class Concentrating(Effect):
    name: str = "Concentrating"
    maintained_effect: Optional[Effect] = None
    maintained_target: Optional[Combatant] = None

    def on_remove(self, target: Combatant) -> None:
        if self.maintained_target is not None and self.maintained_effect is not None:
            self.maintained_target.remove_effect(self.maintained_effect)

    def on_damage_taken(self, target: Combatant, amount: int) -> None:
        advantage, disadvantage = resolve_advantage(target, RollType.SAVE, ability = Ability.CONSTITUTION)
        if not saving_throw(target, Ability.CONSTITUTION, max(10, amount // 2), advantage, disadvantage):
            target.remove_effect(self)
            if self.maintained_target is not None and self.maintained_effect is not None:
                self.maintained_target.remove_effect(self.maintained_effect)

@dataclass
class Frightened(Effect):
    name: str = "Frightened"
    source: Optional[Combatant] = None

    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and roll_context.is_roller

    def forbids_approaching(self, other: Combatant) -> bool:
        return other is self.source

@dataclass
class Invisible(Effect):
    name: str = "Invisible"
    
    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and roll_context.is_roller

    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller

@dataclass
class Paralysed(Effect):
    name: str = "Paralysed"
    duration: int = 10
    prevent_turn: bool = True
    auto_crit_in_melee: bool = True

    def auto_fails_save(self, ability: Ability) -> bool:
        return ability in (Ability.STRENGTH, Ability.DEXTERITY)

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller

    def on_turn_end(self, target: Combatant) -> None:
        advantage, disadvantage = resolve_advantage(target, RollType.SAVE, ability = Ability.WISDOM)
        if saving_throw(target, Ability.WISDOM, self.save_dc, advantage, disadvantage):
            target.remove_effect(self)

@dataclass
class Poisoned(Effect):
    name: str = "Poisoned"

    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and roll_context.is_roller

@dataclass
class Prone(Effect):
    name: str = "Prone"

    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        return (roll_context.roll_type == RollType.ATTACK and roll_context.is_roller) or (roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller and isinstance(roll_context.weapon, RangedWeapon))

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller and isinstance(roll_context.weapon, MeleeWeapon)

@dataclass
class Restrained(Effect):
    name: str = "Restrained"

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller
    
    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and roll_context.is_roller

@dataclass
class Stunned(Effect):
    name: str = "Stunned"
    prevent_turn: bool = True

    def auto_fails_save(self, ability: Ability) -> bool:
        return ability in (Ability.STRENGTH, Ability.DEXTERITY)

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller

@dataclass
class Unconscious(Effect):
    name: str = "Unconscious"
    prevent_turn: bool = True
    auto_crit_in_melee: bool = True

    def auto_fails_save(self, ability: Ability) -> bool:
        return ability in (Ability.STRENGTH, Ability.DEXTERITY)

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller

EFFECT_REGISTRY: dict[str, type[Effect]] = {
    cls.name: cls for cls in Effect.__subclasses__()
}