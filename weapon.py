from abc import ABC, abstractmethod
from dataclasses import dataclass

from enums import DamageType

@dataclass
class Weapon(ABC):
    name: str
    damage_dice: int
    damage_sides: int
    damage_type: DamageType

    @property
    @abstractmethod
    def range(self) -> int:
        pass

@dataclass
class MeleeWeapon(Weapon):
    reach: int
    finesse: bool
    is_off_hand: bool = False

    @property
    def range(self) -> int:
        return self.reach

@dataclass
class RangedWeapon(Weapon):
    optimal_distance: int
    maximum_distance: int
    thrown: bool = False

    @property
    def range(self) -> int:
        return self.maximum_distance