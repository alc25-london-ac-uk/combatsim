from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from combatant import Combatant, Ability

def roll_d20(advantage: bool = False, disadvantage: bool = False) -> int:
    roll_1 = random.randint(1,20)

    if advantage == disadvantage:
        return roll_1
    else:
        roll_2 = random.randint(1,20)

        if advantage:
            return max(roll_1, roll_2)
        else:
            return min(roll_1, roll_2)

def saving_throw(combatant: Combatant, ability: Ability, difficulty: int, advantage: bool = False, disadvantage: bool = False) -> bool:
    roll = roll_d20(advantage, disadvantage) + combatant.ability_scores.modifier_for(ability)
    return roll >= difficulty 

