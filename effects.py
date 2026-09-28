from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import random
from dataclasses import dataclass
from abc import ABC

from dice import saving_throw, RollContext, resolve_advantage
from enums import Ability, RollType

if TYPE_CHECKING:
    from combatant import Combatant

@dataclass
class Effect(ABC):
    name: str = ""
    duration: Optional[int] = None
    save_dc: int = 0
    levels_upcast: int = 0

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

@dataclass
class AcidArrow(Effect):
    name: str = "Acid Arrow"

    def on_turn_end(self, target: Combatant) -> None:
        damage = 0
        for i in range(0,self.levels_upcast + 2):
            damage += random.randint(1, 4)
        target.take_damage(damage)
        target.remove_effect(self)

@dataclass
class Barkskin(Effect):
    name: str = "Barkskin"
    previous_ac: int = 0

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

    def on_damage_taken(self, target: Combatant, amount: int) -> None:
        advantage, disadvantage = resolve_advantage(target, RollType.SAVE, ability = Ability.CONSTITUTION)
        if not saving_throw(target, Ability.CONSTITUTION, max(10, amount // 2), advantage, disadvantage):
            target.remove_effect(self)
            if self.maintained_target is not None and self.maintained_effect is not None:
                self.maintained_target.remove_effect(self.maintained_effect)

# TODO: implement
@dataclass
class Frightened(Effect):
    name: str = "Frightened"
    # Disadvantage on attack rolls

# TODO: implmement
@dataclass
class Invisible(Effect):
    name: str = "Invisible"
    # Advantage on attack rolls, disadvantage on being attacked

@dataclass
class Paralysed(Effect):
    name: str = "Paralysed"

    def on_turn_end(self, target: Combatant) -> None:
        advantage, disadvantage = resolve_advantage(target, RollType.SAVE, ability = Ability.WISDOM)
        if saving_throw(target, Ability.WISDOM, self.save_dc, advantage, disadvantage):
            target.remove_effect(self)

# TODO: implmement
@dataclass
class Poisoned(Effect):
    name: str = "Poisoned"
    # Disadvantage on attack rolls

# TODO: implmement
@dataclass
class Prone(Effect):
    name: str = "Prone"
    # Attacks have disadvantage, melee attacks against have advantage, ranged attacks against have disadvantage

# TODO: implement
@dataclass
class Restrained(Effect):
    name: str = "Restrained"
    # Same advantage / disadvantage as blind

# TODO: immplement
@dataclass
class Stunned(Effect):
    name: str = "Stunned"
    # Same as paralysed but without auto-crit

# TODO: implement
@dataclass
class Unconscious(Effect):
    name: str = "Unconscious"
    # Same as paralysed


EFFECT_REGISTRY: dict[str, type[Effect]] = {
    cls.name: cls for cls in Effect.__subclasses__()
}