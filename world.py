from typing import TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from combatant import Combatant

@dataclass
class Position:
    x: int
    y: int

@dataclass
class Grid:
    width: int
    height: int
    positions: dict[Combatant, Position] = field(default_factory = dict)

    def place(self, combatant: Combatant, x: int, y: int) -> Position:
        new_position = Position(x, y)
        self.positions[combatant] = new_position
        return new_position
    
    def position_of(self, combatant: Combatant) -> Position:
        return self.positions[combatant]
    
    def distance(self, a: Combatant, b: Combatant) -> int:
        position_a, position_b = self.position_of(a), self.position_of(b)
        return max(abs(position_a.x - position_b.x), abs(position_a.y - position_b.y)) * 5

    def move_towards(self, a: Combatant, b: Combatant) -> Position:
        position_a, position_b = self.position_of(a), self.position_of(b)
        
        dx = position_b.x - position_a.x
        dy = position_b.y - position_a.y

        move_x = (dx > 1) - (dx < -1)
        move_y = (dy > 1) - (dy < -1)

        return self.place(a, position_a.x + move_x, position_a.y + move_y)
    
    def enemies_in_melee_range(self, combatant: Combatant) -> bool:
        return any(
            c for c in self.positions
            if c.team != combatant.team
            and self.distance(combatant, c) <= 5
        )

    def combatants_in_range(self, combatant: Combatant, range: int) -> list[Combatant]:
        return [
            c for c in self.positions
            if c is not combatant
            and self.distance(combatant, c) <= range
            and c.alive
        ]

@dataclass
class CombatState:
    grid: Grid
    initiative_order: list[Combatant]