from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import random
from dataclasses import dataclass, field
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
    ac_bonus: int = 0 # added to the target's base armour class while the effect lasts
    ac_floor: int = 0 # the target's armour class cannot be lower than this while the effect lasts
    immobilises: bool = False # the target's speed becomes 0 while the effect lasts
    break_free_ability: Optional[Ability] = None # if set, the target can spend its action on a check with this ability against save_dc to end the effect

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

    def ac_gain(self, target: Combatant) -> int:
        """How much armour class applying this effect would add, given what the target already has."""
        return target.armour_class_with(target.effects + [self]) - target.ac

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
    duration: int = 10
    ac_floor: int = 16

@dataclass
class ShieldOfFaith(Effect):
    name: str = "Shield of Faith"
    duration: int = 100
    ac_bonus: int = 2

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
    more_maintained: list = field(default_factory = list) # further (target, effect) pairs, for a spell that holds several targets at once

    def maintain(self, target: Combatant, effect: Effect) -> None:
        if self.maintained_effect is None:
            self.maintained_target, self.maintained_effect = target, effect
        else:
            self.more_maintained.append((target, effect))

    def release_everything(self) -> None:
        pairs = [(self.maintained_target, self.maintained_effect)] + self.more_maintained
        for target, effect in pairs:
            if target is not None and effect is not None:
                target.remove_effect(effect)

    def on_remove(self, target: Combatant) -> None:
        self.release_everything()

    def on_damage_taken(self, target: Combatant, amount: int) -> None:
        advantage, disadvantage = resolve_advantage(target, RollType.SAVE, ability = Ability.CONSTITUTION)
        if not saving_throw(target, Ability.CONSTITUTION, max(10, amount // 2), advantage, disadvantage):
            target.remove_effect(self) # which releases everything it was maintaining

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
    immobilises: bool = True
    break_free_ability: Optional[Ability] = Ability.STRENGTH

    def grants_advantage(self, roll_context: RollContext) -> bool:
        return roll_context.roll_type == RollType.ATTACK and not roll_context.is_roller

    def grants_disadvantage(self, roll_context: RollContext) -> bool:
        if roll_context.roll_type == RollType.ATTACK:
            return roll_context.is_roller
        return roll_context.roll_type == RollType.SAVE and roll_context.is_roller and roll_context.ability == Ability.DEXTERITY

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