from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import random
from dataclasses import dataclass
from abc import ABC

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

# TODO: Add advantage / disadvantage to attacks once these principles exist in the engine
@dataclass
class Blind(Effect):
    name: str = "Blind"

@dataclass
class Concentrating(Effect):
    name: str = "Concentrating"
    maintained_effect: Optional[Effect] = None
    maintained_target: Optional[Combatant] = None

    def on_damage_taken(self, target: Combatant, amount: int) -> None:
        dc = max(10, amount // 2)
        save_roll = random.randint(1, 20) + target.ability_scores.con_mod
        if save_roll < dc:
            target.remove_effect(self)
            if self.maintained_target is not None and self.maintained_effect is not None:
                self.maintained_target.remove_effect(self.maintained_effect)

@dataclass
class Paralysed(Effect):
    name: str = "Paralysed"

    def on_turn_end(self, target: Combatant) -> None:
        save_roll = random.randint(1, 20) + target.ability_scores.wis_mod
        if save_roll > self.save_dc:
            target.remove_effect(self)

EFFECT_REGISTRY: dict[str, type[Effect]] = {
    cls.name: cls for cls in Effect.__subclasses__()
}