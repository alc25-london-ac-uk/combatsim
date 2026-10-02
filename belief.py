from dataclasses import dataclass, field

from combatant import Combatant, Monster, PlayerCharacter
from enums import DamageType
from effects import Concentrating

PC_HIT_DICE = {"cleric": 8, "rogue": 8, "fighter": 10, "wizard": 6}
PC_CON_MOD_RANGE = range(-1, 5)
SPELLCASTING_MISATTRIBUTION_RATE = 0.05
TYPICAL_CON_SAVE_MOD_RANGE = range(-1, 5)
SLOT_DEPLETION_STEP = 0.3
DEFAULT_DAMAGE_MULTIPLIER = 1.0
MITIGATION_UPDATE_STEP = 0.5

def _bayesian_update(belief: float, misattribution_rate: float = SPELLCASTING_MISATTRIBUTION_RATE) -> float:
    true_positive = (1 - misattribution_rate) * belief
    false_positive = misattribution_rate * (1 - belief)
    return true_positive / (true_positive + false_positive)

def _typical_concentration_save_probability(damage: int) -> float:
    save_dc = max(10, damage // 2)
    probabilities = [max(0, min(1, (21 - (save_dc - con_mod)) / 20)) for con_mod in TYPICAL_CON_SAVE_MOD_RANGE]
    return sum(probabilities) / len(probabilities)

def _triangular_distribution(center: int, half_width: int, floor: int, ceiling: int) -> dict[int, float]:
    half_width = max(2, half_width)
    low = max(floor, round(center - half_width))
    high = min(ceiling, round(center + half_width))

    weights: dict[int, float] = {}
    for hp in range(low, high + 1):
        weight = max(0.0, 1 - abs(hp - center) / half_width)
        if weight > 0:
            weights[hp] = weight

    total = sum(weights.values())
    return {hp: weight / total for hp, weight in weights.items()}

@dataclass
class CombatantBelief:
    hypotheses: dict[tuple[int, int], float]
    offensive_capable: float = 0.5
    healer_capable: float = 0.5
    concentrating: float = 0.0
    depleted: float = 0.0
    damage_multipliers: dict[DamageType, float] = field(default_factory = dict)

    @staticmethod
    def for_monster(max_hp: int, spread_fraction: float = 0.15) -> "CombatantBelief":
        half_width = max(2, round(max_hp * spread_fraction))
        max_hp_distribution = _triangular_distribution(center = max_hp, half_width = half_width, floor = 1, ceiling = max_hp + half_width)
        hypotheses = {(candidate, candidate): probability for candidate, probability in max_hp_distribution.items()}
        return CombatantBelief(hypotheses = hypotheses)

    @staticmethod
    def for_player_character(character_class: str, level: int) -> "CombatantBelief":
        hit_dice = PC_HIT_DICE.get(character_class, 8)

        estimates = []
        for con_mod in PC_CON_MOD_RANGE:
            first_level = hit_dice + con_mod
            subsequent_levels = (hit_dice // 2 + 1 + con_mod) * (level - 1)
            estimates.append(max(1, first_level + subsequent_levels))

        hypotheses: dict[tuple[int, int], float] = {}
        weight = 1 / len(estimates)
        for estimate in estimates:
            key = (estimate, estimate)
            hypotheses[key] = hypotheses.get(key, 0.0) + weight

        return CombatantBelief(hypotheses = hypotheses)

    @staticmethod
    def initial_prior_for(combatant: Combatant) -> "CombatantBelief":
        if isinstance(combatant, Monster):
            return CombatantBelief.for_monster(combatant.max_hp)
        elif isinstance(combatant, PlayerCharacter):
            return CombatantBelief.for_player_character(combatant.character_class, combatant.level)
        else:
            raise TypeError(f"No belief prior defined for combatant type {type(combatant).__name__}")

    @staticmethod
    def ground_truth_for(combatant: Combatant) -> "CombatantBelief":
        offensive_capable = 1.0 if any(not spell.is_healing for spell in combatant.spells) else 0.0
        healer_capable = 1.0 if any(spell.is_healing for spell in combatant.spells) else 0.0
        concentrating = 1.0 if combatant.has_effect(Concentrating) else 0.0
        depleted = 0.0 if any(count > 0 for count in combatant.spell_slots.values()) else 1.0

        damage_multipliers = {}
        for damage_type in combatant.damage_resistances:
            damage_multipliers[damage_type] = 0.5
        for damage_type in combatant.damage_vulnerabilities:
            damage_multipliers[damage_type] = 2.0
        for damage_type in combatant.damage_immunities:
            damage_multipliers[damage_type] = 0.0

        return CombatantBelief(
            hypotheses = {(combatant.hp, combatant.max_hp): 1.0},
            offensive_capable = offensive_capable,
            healer_capable = healer_capable,
            concentrating = concentrating,
            depleted = depleted,
            damage_multipliers = damage_multipliers
        )

    def observe_damage(self, damage: int) -> None:
        new_hypotheses: dict[tuple[int, int], float] = {}
        for (hp, max_hp), probability in self.hypotheses.items():
            key = (max(0, hp - damage), max_hp)
            new_hypotheses[key] = new_hypotheses.get(key, 0.0) + probability
        self.hypotheses = new_hypotheses

        self.concentrating *= _typical_concentration_save_probability(damage)

    def observe_healing(self, amount: int) -> None:
        new_hypotheses: dict[tuple[int, int], float] = {}
        for (hp, max_hp), probability in self.hypotheses.items():
            key = (min(max_hp, hp + amount), max_hp)
            new_hypotheses[key] = new_hypotheses.get(key, 0.0) + probability
        self.hypotheses = new_hypotheses

    def observe_offensive_cast(self) -> None:
        self.offensive_capable = _bayesian_update(self.offensive_capable)

    def observe_healing_cast(self) -> None:
        self.healer_capable = _bayesian_update(self.healer_capable)

    def observe_concentration_spell_cast(self) -> None:
        self.concentrating = 1 - SPELLCASTING_MISATTRIBUTION_RATE

    def observe_leveled_spell_cast(self) -> None:
        still_has_slots = (1 - self.depleted) * (1 - SLOT_DEPLETION_STEP)
        self.depleted = 1 - still_has_slots

    def damage_multiplier(self, damage_type: DamageType) -> float:
        return self.damage_multipliers.get(damage_type, DEFAULT_DAMAGE_MULTIPLIER)

    def observe_damage_mitigation(self, damage_type: DamageType, expected_damage: int, actual_damage: int) -> None:
        if expected_damage <= 0:
            return

        observed_ratio = actual_damage / expected_damage
        current = self.damage_multiplier(damage_type)
        self.damage_multipliers[damage_type] = current + MITIGATION_UPDATE_STEP * (observed_ratio - current)

    def expected_hp(self) -> float:
        return sum(hp * probability for (hp, max_hp), probability in self.hypotheses.items())

    @property
    def believed_max_hp(self) -> float:
        return sum(max_hp * probability for (hp, max_hp), probability in self.hypotheses.items())

    @property
    def hp_distribution(self) -> dict[int, float]:
        marginal: dict[int, float] = {}
        for (hp, max_hp), probability in self.hypotheses.items():
            marginal[hp] = marginal.get(hp, 0.0) + probability
        return marginal

    def probability_at_or_below(self, threshold: int) -> float:
        return sum(probability for (hp, max_hp), probability in self.hypotheses.items() if hp <= threshold)

    def bracket_probabilities(self) -> dict[str, float]:
        probabilities = {"critical": 0.0, "bloodied": 0.0, "healthy": 0.0}
        for (hp, max_hp), probability in self.hypotheses.items():
            fraction = hp / max_hp if max_hp > 0 else 0.0
            if fraction < 0.10:
                probabilities["critical"] += probability
            elif fraction < 0.50:
                probabilities["bloodied"] += probability
            else:
                probabilities["healthy"] += probability
        return probabilities