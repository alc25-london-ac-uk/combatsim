from __future__ import annotations
from typing import Optional
import random
from typing import TYPE_CHECKING
from dataclasses import dataclass

from enums import RollType, AttackResult
from world import Grid, CombatState
from weapon import Weapon, RangedWeapon

if TYPE_CHECKING:
    from combatant import Combatant, Ability
    from spell import Spell

@dataclass
class RollContext:
    roll_type: RollType
    is_roller: bool
    other: Optional[Combatant] = None
    ability: Optional[Ability] = None
    weapon: Optional[Weapon] = None
    spell: Optional[Spell] = None

def resolve_advantage(actor: Combatant, roll_type: RollType, *, other: Optional[Combatant] = None, ability: Optional[Ability] = None, weapon: Optional[Weapon] = None, spell: Optional[Spell] = None, combat_state: Optional[CombatState] = None) -> tuple[bool, bool]:
    advantage = False
    disadvantage = False

    if combat_state is not None and other is not None and roll_type == RollType.ATTACK and isinstance(weapon, RangedWeapon):
        # Ranged attack while enemy within 5ft and can see you = disadvantage
        if combat_state.grid.enemies_in_melee_range(actor):
            disadvantage = True

        # Attacking beyond ranged weapon normal range = disadvantage
        if combat_state.grid.distance(actor, other) > weapon.optimal_distance:
            disadvantage = True

    # Effects on action's actor that grant advantage / disadvantage
    actor_context = RollContext(roll_type, True, other = other, ability = ability, weapon = weapon, spell = spell)
    for e in actor.effects:
        if e.grants_advantage(actor_context):
            advantage = True
        if e.grants_disadvantage(actor_context):
            disadvantage = True

    # Effects on action's target that grant advantage / disadvantage
    if other is not None:
        other_context = RollContext(roll_type, False, other = actor, ability = ability, weapon = weapon, spell = spell)
        for e in other.effects:
            if e.grants_advantage(other_context):
                advantage = True
            if e.grants_disadvantage(other_context):
                disadvantage = True

    return advantage, disadvantage

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
    if any(e.auto_fails_save(ability) for e in combatant.effects):
        return False
    
    roll = roll_d20(advantage, disadvantage) + combatant.ability_scores.modifier_for(ability)
    
    return roll >= difficulty

def attack_roll(bonus: int, target_ac: int, advantage: bool = False, disadvantage: bool = False) -> AttackResult:
    roll = roll_d20(advantage, disadvantage)
    
    if roll == 20:
        return AttackResult.CRIT
    
    if roll + bonus > target_ac:
        return AttackResult.HIT
    
    return AttackResult.MISS

def damage_roll(damage_dice: int, damage_sides: int, bonus: int, is_crit: bool) -> int:
    damage = 0
    
    if damage_dice > 0:
        for _ in range(damage_dice):
            damage += random.randint(1, damage_sides)

        if is_crit:
            damage *= 2

        damage += bonus

    return damage