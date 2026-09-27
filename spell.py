from typing import Optional
from dataclasses import dataclass

from enums import TargetType, DamageType, Ability
from effects import Effect

# TODO: area-effect spells
# TODO: delayed-effect spells
# TODO: control spells
# TODO: concentration
# TODO: levelled cantrips
# TODO: upcasting
# TODO: healing spells
# TODO: Summons
# TODO: Buffs
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
    damage_dice_on_miss: int = 0
    damage_pct_on_save: float = 0
    concentration: bool = False
    effect: Optional[type[Effect]] = None
    upcastable_extra_damage_die: bool = False
    upcastable_extra_target: bool = False

    @property
    def is_cantrip(self) -> bool:
        return self.level == 0