from typing import Any

from world import Grid, Position

def test_distance_is_chebyshev_scaled_by_five_feet():
    grid = Grid(10, 10)
    a: Any = object()
    b: Any = object()
    grid.place(a, 0, 0)
    grid.place(b, 3, 1)
    # Chebyshev distance is max(dx, dy), not the diagonal (Euclidean) distance
    assert grid.distance(a, b) == 15

def test_diagonal_distance_costs_the_same_as_orthogonal():
    grid = Grid(10, 10)
    a: Any = object()
    b: Any = object()
    grid.place(a, 0, 0)
    grid.place(b, 2, 2)
    assert grid.distance(a, b) == 10

def test_move_towards_steps_one_square_per_call():
    grid = Grid(10, 10)
    a: Any = object()
    b: Any = object()
    grid.place(a, 0, 0)
    grid.place(b, 5, 5)
    new_position = grid.move_towards(a, b)
    assert new_position == Position(1, 1)

def test_move_towards_does_not_move_when_already_adjacent():
    grid = Grid(10, 10)
    a: Any = object()
    b: Any = object()
    grid.place(a, 0, 0)
    grid.place(b, 1, 0)
    new_position = grid.move_towards(a, b)
    assert new_position == Position(0, 0)

def test_move_towards_handles_pure_vertical_and_horizontal_movement():
    grid = Grid(10, 10)
    a: Any = object()
    b: Any = object()
    grid.place(a, 5, 5)
    grid.place(b, 5, 0) # directly below, same x
    new_position = grid.move_towards(a, b)
    assert new_position == Position(5, 4)

class _Fake:
    def __init__(self, team):
        self.team = team

def test_enemies_in_melee_range_ignores_same_team():
    grid = Grid(10, 10)

    mover: Any = _Fake("party")
    ally: Any = _Fake("party")

    grid.place(mover, 0, 0)
    grid.place(ally, 0, 1) # adjacent, but same team

    assert grid.enemies_in_melee_range(mover) is False

def test_enemies_in_melee_range_detects_adjacent_hostiles():
    grid = Grid(10, 10)

    mover: Any = _Fake("party")
    enemy_adjacent: Any = _Fake("enemies")
    enemy_far: Any = _Fake("enemies")

    grid.place(mover, 0, 0)
    grid.place(enemy_adjacent, 0, 1) # 5ft away
    grid.place(enemy_far, 0, 5) # 25ft away

    assert grid.enemies_in_melee_range(mover) is True

def test_enemies_in_melee_range_false_when_all_hostiles_are_far():
    grid = Grid(10, 10)

    mover: Any = _Fake("party")
    enemy_far: Any = _Fake("enemies")

    grid.place(mover, 0, 0)
    grid.place(enemy_far, 0, 5)

    assert grid.enemies_in_melee_range(mover) is False
