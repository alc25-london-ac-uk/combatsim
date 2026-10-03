from typing import Optional
from dataclasses import dataclass

from enums import TargetType, DamageType, Ability
from effects import Effect

# TODO: delayed-effect spells
# TODO: upcasting
# TODO: Summons
@dataclass
class Spell:
    name: str
    level: int
    target_type: Optional[TargetType]
    damage_type: Optional[DamageType]
    damage_dice: int
    damage_sides: int
    range: int
    requires_attack_roll: bool
    save_allowed: bool
    save_attribute: Ability
    aoe_radius: int = 0
    is_healing: bool = False
    damage_dice_on_miss: int = 0
    damage_pct_on_save: float = 0
    concentration: bool = False
    effect: Optional[type[Effect]] = None
    upcastable_extra_damage_die: bool = False
    upcastable_extra_target: bool = False
    is_bonus_action: bool = False
    damage_bonus: int = 0
    ray_count: int = 1

    @property
    def is_cantrip(self) -> bool:
        return self.level == 0