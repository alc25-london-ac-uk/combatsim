from typing import Any

from dice import attack_roll, roll_d20, damage_roll, saving_throw
from enums import AttackResult, Ability

def test_attack_roll_hits_when_beating_ac(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 15)
    result = attack_roll(bonus = 3, target_ac = 17) # 15 + 3 = 18 > 17
    assert result == AttackResult.HIT

def test_attack_roll_nat_20_is_always_crit(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 20)
    result = attack_roll(bonus = -5, target_ac = 100) # would fail on any other roll
    assert result == AttackResult.CRIT

def test_attack_roll_misses_when_not_beating_ac(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 10)
    result = attack_roll(bonus = 2, target_ac = 15) # 10 + 2 = 12, not > 15
    assert result == AttackResult.MISS

def test_attack_roll_exact_tie_with_ac_is_a_miss(monkeypatch):
    # 5e rule: you must beat AC, meeting it exactly is a miss
    monkeypatch.setattr("dice.random.randint", lambda a, b: 10)
    result = attack_roll(bonus = 5, target_ac = 15) # 10 + 5 = 15, not > 15
    assert result == AttackResult.MISS

def test_advantage_takes_higher_roll(monkeypatch):
    rolls = iter([3, 17])
    monkeypatch.setattr("dice.random.randint", lambda a, b: next(rolls))
    assert roll_d20(advantage = True) == 17

def test_disadvantage_takes_lower_roll(monkeypatch):
    rolls = iter([3, 17])
    monkeypatch.setattr("dice.random.randint", lambda a, b: next(rolls))
    assert roll_d20(disadvantage = True) == 3

def test_advantage_and_disadvantage_together_cancel_out(monkeypatch):
    # 5e rule: having both cancels to a single flat roll, no re-roll at all
    calls = []
    def fake_randint(a, b):
        calls.append(1)
        return 12
    monkeypatch.setattr("dice.random.randint", fake_randint)
    assert roll_d20(advantage = True, disadvantage = True) == 12
    assert len(calls) == 1

def test_damage_roll_sums_dice_and_adds_bonus(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    assert damage_roll(damage_dice = 3, damage_sides = 6, bonus = 2, is_crit = False) == 14 # (4+4+4) + 2

def test_damage_roll_crit_doubles_dice_but_not_bonus(monkeypatch):
    # 5e rule: a crit doubles the dice rolled, not the flat modifier
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    assert damage_roll(damage_dice = 2, damage_sides = 6, bonus = 5, is_crit = True) == 21 # (4+4)*2 + 5

def test_damage_roll_with_zero_dice_ignores_bonus(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 4)
    assert damage_roll(damage_dice = 0, damage_sides = 6, bonus = 5, is_crit = False) == 0

class _FakeAbilityScores:
    def modifier_for(self, ability):
        return 2

class _FakeEffect:
    def __init__(self, auto_fails = False):
        self._auto_fails = auto_fails

    def auto_fails_save(self, ability):
        return self._auto_fails

class _FakeCombatant:
    def __init__(self, effects = None):
        self.ability_scores = _FakeAbilityScores()
        self.effects = effects or []

def test_saving_throw_succeeds_when_total_meets_difficulty(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 10)
    combatant: Any = _FakeCombatant()
    assert saving_throw(combatant, Ability.STRENGTH, difficulty = 12) is True # 10 + 2 = 12

def test_saving_throw_fails_when_total_is_below_difficulty(monkeypatch):
    monkeypatch.setattr("dice.random.randint", lambda a, b: 10)
    combatant: Any = _FakeCombatant()
    assert saving_throw(combatant, Ability.STRENGTH, difficulty = 13) is False # 10 + 2 = 12

def test_saving_throw_auto_fails_regardless_of_roll(monkeypatch):
    # e.g. Paralysed/Stunned auto-failing STR/DEX saves, even on a roll that would otherwise succeed
    monkeypatch.setattr("dice.random.randint", lambda a, b: 20)
    combatant: Any = _FakeCombatant(effects = [_FakeEffect(auto_fails = True)])
    assert saving_throw(combatant, Ability.STRENGTH, difficulty = 1) is False