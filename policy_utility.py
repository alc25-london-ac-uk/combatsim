from abc import abstractmethod
from typing import Optional

from enums import TargetType, TargetPriority
from weapon import Weapon, MeleeWeapon, RangedWeapon
from spell import Spell
from effects import Concentrating
from actions import ActionType, Action, determine_targets, spell_flat_bonus
from world import CombatState
from combatant import Combatant
from policy import Policy
from belief import CombatantBelief, belief_vs_truth

HEALER_PRIORITY_WEIGHT = 1.5
CONCENTRATION_PRIORITY_WEIGHT = 1.0
OFFENSIVE_PRIORITY_WEIGHT = 0.5

BUFF_HORIZON_ROUNDS = 3
APPROACH_WEIGHT = 0.1

EXPLORATION_BONUS = 0.25
EXPLORE_WITH_SPELLS = False

NEAREST_WEIGHT = 0.05
WEAKEST_WEIGHT = 2.0
HIGHEST_THREAT_WEIGHT = 1.0

EXPLAINED_CANDIDATES = 5

class UtilityPolicy(Policy):
    explanations: Optional[list] = None
    _candidate_log: Optional[list] = None

    @abstractmethod
    def _belief_for(self, target: Combatant, beliefs: dict[Combatant, CombatantBelief]) -> CombatantBelief:
        pass

    def _ally_buff_value(self, combatant: Combatant, ally: Combatant, spell: Spell, combat_state: CombatState) -> float:
        """Expected damage prevented over the next few rounds by the armour class the buff grants this ally."""
        if ally.has_effect(spell.effect):
            return -1.0

        ac_gain = spell.effect().ac_gain(ally)
        if ac_gain <= 0:
            return -1.0

        living_allies = sum(1 for c in combat_state.initiative_order if c.alive and c.team == combatant.team)
        incoming_per_round = 0.0
        for enemy in combat_state.initiative_order:
            if not enemy.alive or enemy.team == combatant.team or not enemy.weapons:
                continue
            best_hit_damage = max(
                weapon.damage_dice * (weapon.damage_sides + 1) / 2 + enemy.get_damage_bonus(weapon)
                for weapon in enemy.weapons
            )
            incoming_per_round += enemy.attack_count * best_hit_damage

        # each point of AC removes one twentieth of the hits; the enemy's attacks are assumed to be spread evenly over the allies
        return ac_gain / 20 * incoming_per_round / max(1, living_allies) * BUFF_HORIZON_ROUNDS

    def _view_of(self, combatant: Combatant, target: Combatant, beliefs: dict[Combatant, CombatantBelief]) -> CombatantBelief:
        # Only opponents are hidden: a combatant knows the true state of itself and its allies
        if target.team == combatant.team:
            return CombatantBelief.ground_truth_for(target)
        return self._belief_for(target, beliefs)

    def _expected_damage_multiplier(self, belief: CombatantBelief, damage_type, explore: bool = True) -> float:
        if explore and not belief.has_tested(damage_type):
            return 1.0 + EXPLORATION_BONUS
        return belief.damage_multiplier(damage_type)

    def _priority_bonus(self, belief: CombatantBelief) -> float:
        remaining_resource_confidence = 1 - belief.depleted
        return (
            belief.healer_capable * remaining_resource_confidence * HEALER_PRIORITY_WEIGHT
            + belief.concentrating * CONCENTRATION_PRIORITY_WEIGHT
            + belief.offensive_capable * remaining_resource_confidence * OFFENSIVE_PRIORITY_WEIGHT
        )

    def _target_priority_bonus(self, combatant: Combatant, target: Combatant, distance: int, belief: CombatantBelief) -> float:
        profile = combatant.ai.profile
        if profile is None:
            return 0.0

        match profile.target_priority:
            case TargetPriority.NEAREST:
                return -distance * NEAREST_WEIGHT
            case TargetPriority.WEAKEST:
                believed_hp_fraction = belief.expected_hp() / belief.believed_max_hp if belief.believed_max_hp > 0 else 0.0
                return (1 - believed_hp_fraction) * WEAKEST_WEIGHT
            case TargetPriority.HIGHEST_THREAT:
                return self._priority_bonus(belief) * HIGHEST_THREAT_WEIGHT

        return 0.0

    def decide(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> Action:
        self._candidate_log = [] if self.explanations is not None else None

        action_candidates = [
            self.best_spell(combatant, combat_state, beliefs, bonus_action),
            self.best_attack(combatant, combat_state, beliefs, bonus_action)
        ]

        best_score, best_action = max(action_candidates, key = lambda c: c[0])
        if self.explanations is not None:
            self.explanations.append(self._explain(combatant, combat_state, beliefs, bonus_action, best_action))

        if best_action is not None:
            combined_rationale = " | ".join(
                action.rationale
                for _, action in action_candidates
                if action is not None
            )
            best_action.rationale = f"{best_action.rationale} [vs: {combined_rationale}]"

        return best_action or Action(ActionType.NONE, combatant)

    def _explain(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool, chosen: Optional[Action]) -> dict:
        chosen_key = None
        if chosen is not None:
            chosen_key = (chosen.target.name, chosen.weapon.name if chosen.weapon else chosen.spell.name)

        usable = [c for c in self._candidate_log if c["total"] > -1.0] # -1 marks "cannot be done at all"
        usable.sort(key = lambda c: c["total"], reverse = True)
        candidates = [
            {**c, "chosen": (c["target"], c["label"]) == chosen_key}
            for c in usable[:EXPLAINED_CANDIDATES]
        ]
        if chosen_key is not None and not any(c["chosen"] for c in candidates):
            candidates += [{**c, "chosen": True} for c in usable if (c["target"], c["label"]) == chosen_key]

        enemies = [e for e in combat_state.initiative_order if e.alive and e.team != combatant.team]
        return {
            "combatant": combatant.name,
            "bonus_action": bonus_action,
            "chosen": None if chosen is None else {"kind": chosen.action_type.name.lower(), "target": chosen.target.name, "label": chosen_key[1]},
            "candidates": candidates,
            "beliefs": [belief_vs_truth(self._belief_for(enemy, beliefs), enemy) | {"name": enemy.name} for enemy in enemies],
        }

    def best_attack(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        best_score = -1.0
        best_action = None

        for target in combat_state.initiative_order:
            if target.alive:
                if target.team != combatant.team:
                    for weapon in combatant.weapons:
                        if (isinstance(weapon, MeleeWeapon) and weapon.is_off_hand) == bonus_action:
                            score = self.score_attack(combatant, target, weapon, combat_state, beliefs)
                            if self._candidate_log is not None:
                                self._candidate_log.append({"kind": "attack", "label": weapon.name, "target": target.name, "total": score,
                                                            "terms": self._attack_terms(combatant, target, weapon, combat_state, beliefs)})
                            if score > best_score:
                                best_score = score
                                best_action = Action(ActionType.ATTACK, target, rationale = f"attack score: {score:.2f}", weapon = weapon)

        return best_score, best_action

    def _approach_score(self, combatant: Combatant, target: Combatant, distance: int, action_range: int) -> Optional[float]:
        if distance - action_range <= combatant.movement:
            return None

        movement_penalty = max(0, distance - action_range) / combatant.speed
        if any(e.forbids_approaching(target) for e in combatant.effects):
            movement_penalty = 100
        return -APPROACH_WEIGHT * movement_penalty

    def score_attack(self, combatant: Combatant, target: Combatant, weapon: Weapon, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> float:
        return sum(self._attack_terms(combatant, target, weapon, combat_state, beliefs).values())

    def _attack_terms(self, combatant: Combatant, target: Combatant, weapon: Weapon, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> dict[str, float]:
        approach_score = self._approach_score(combatant, target, combat_state.grid.distance(combatant, target), weapon.range)
        if approach_score is not None:
            return {"approach_penalty": approach_score}

        belief = self._view_of(combatant, target, beliefs)
        hit_probability = belief.hit_probability(combatant.get_attack_bonus(weapon))

        if isinstance(weapon, RangedWeapon) and combat_state.grid.enemies_in_melee_range(combatant):
            hit_probability *= 0.5

        expected_damage = hit_probability * (
            weapon.damage_dice * (weapon.damage_sides + 1) / 2
            + combatant.get_damage_bonus(weapon)
        )

        expected_damage *= self._expected_damage_multiplier(belief, weapon.damage_type)
        kill_bonus = belief.probability_at_or_below(round(expected_damage)) * 2.0
        priority_bonus = self._priority_bonus(belief)

        distance = combat_state.grid.distance(combatant, target)
        target_priority_bonus = self._target_priority_bonus(combatant, target, distance, belief)
        movement_penalty = max(0, distance - weapon.range) / combatant.speed
        if any(e.forbids_approaching(target) for e in combatant.effects):
            movement_penalty = 100

        return {
            "expected_damage": expected_damage,
            "kill_bonus": kill_bonus,
            "priority_bonus": priority_bonus,
            "target_priority_bonus": target_priority_bonus,
            "movement_penalty": -movement_penalty,
        }

    def best_spell(self, combatant: Combatant, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief], bonus_action: bool = False) -> tuple[float, Optional[Action]]:
        best_score = -1.0
        best_action = None

        for target in combat_state.initiative_order:
            if target.alive:
                for spell in combatant.spells:
                    if spell.is_bonus_action == bonus_action:
                        if (spell.target_type == TargetType.ENEMY and target.team != combatant.team) or (spell.target_type == TargetType.ALLY and target.team == combatant.team):
                            score = self.score_spell(combatant, target, spell, combat_state, beliefs)
                            if self._candidate_log is not None:
                                self._candidate_log.append({"kind": "spell", "label": spell.name, "target": target.name, "total": score,
                                                            "terms": self._spell_breakdown(combatant, target, spell, combat_state, beliefs)})
                            if score > best_score:
                                best_score = score
                                best_action = Action(ActionType.SPELL, target, rationale = f"spell score: {score:.2f}", spell = spell)

        return best_score, best_action

    def score_spell(self, combatant: Combatant, target: Combatant, spell: Spell, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> float:
        if not spell.is_cantrip and combatant.spell_slots.get(spell.level, 0) == 0:
            return -1.0

        distance = combat_state.grid.distance(combatant, target)
        approach_score = self._approach_score(combatant, target, distance, spell.range)
        if approach_score is not None:
            return approach_score

        movement_penalty = max(0, distance - spell.range) / combatant.speed
        if any(e.forbids_approaching(target) for e in combatant.effects):
            movement_penalty = 100

        concentration_penalty = 3.0 if spell.concentration and combatant.has_effect(Concentrating) else 0.0

        targets = determine_targets(target, spell, combat_state)
        total = sum(self.score_spell_hit(combatant, t, spell, combat_state, beliefs) for t in targets)

        return total - movement_penalty - concentration_penalty

    def _spell_breakdown(self, combatant: Combatant, target: Combatant, spell: Spell, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> dict[str, float]:
        if not spell.is_cantrip and combatant.spell_slots.get(spell.level, 0) == 0:
            return {"no_spell_slot": -1.0}

        distance = combat_state.grid.distance(combatant, target)
        approach_score = self._approach_score(combatant, target, distance, spell.range)
        if approach_score is not None:
            return {"approach_penalty": approach_score}

        terms: dict[str, float] = {}
        for affected in determine_targets(target, spell, combat_state):
            for name, value in self._spell_hit_terms(combatant, affected, spell, combat_state, beliefs).items():
                terms[name] = terms.get(name, 0.0) + value

        terms["movement_penalty"] = -(max(0, distance - spell.range) / combatant.speed)
        if any(e.forbids_approaching(target) for e in combatant.effects):
            terms["movement_penalty"] = -100
        if spell.concentration and combatant.has_effect(Concentrating):
            terms["concentration_penalty"] = -3.0
        return terms

    def score_spell_hit(self, combatant: Combatant, target: Combatant, spell: Spell, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> float:
        return sum(self._spell_hit_terms(combatant, target, spell, combat_state, beliefs).values())

    def _spell_hit_terms(self, combatant: Combatant, target: Combatant, spell: Spell, combat_state: CombatState, beliefs: dict[Combatant, CombatantBelief]) -> dict[str, float]:
        is_ally = target.team == combatant.team
        belief = self._view_of(combatant, target, beliefs)
        believed_hp_fraction = belief.expected_hp() / belief.believed_max_hp if belief.believed_max_hp > 0 else 0.0

        if spell.is_healing:
            if not is_ally:
                return {"not_applicable": -1.0}

            expected_healing = spell.damage_dice * (spell.damage_sides + 1) / 2 + spell_flat_bonus(combatant, spell)
            urgency = 1 - believed_hp_fraction

            return {"healing_value": expected_healing * urgency}

        if spell.effect is not None and spell.damage_dice == 0 and spell.target_type == TargetType.ALLY:
            return {"buff_value": self._ally_buff_value(combatant, target, spell, combat_state)}

        if spell.effect is not None and spell.damage_dice == 0:
            if target.has_effect(spell.effect):
                return {"control_value": 0.0} # already under this effect, so casting it again changes nothing

            threat = believed_hp_fraction
            score = 5.0 * threat

            if is_ally:
                return {"friendly_fire": -score}
            return {"control_value": score, "priority_bonus": self._priority_bonus(belief)}

        if not spell.requires_attack_roll:
            hit_probability = 1
        else:
            hit_probability = belief.hit_probability(combatant.get_spell_attack_bonus())

        rays = spell.ray_count if spell.requires_attack_roll else 1
        expected_damage = rays * hit_probability * (
            (spell.damage_dice + (1 if spell.is_cantrip and combatant.caster_level >= 5 else 0)) * (spell.damage_sides + 1) / 2
            + spell_flat_bonus(combatant, spell)
        )

        if spell.save_allowed:
            save_success_probability = belief.save_success_probability(spell.save_attribute, combatant.spell_save_dc)
            expected_damage = (
                expected_damage * (1 - save_success_probability) +
                expected_damage * spell.damage_pct_on_save * save_success_probability
            )

        if spell.damage_type is not None:
            expected_damage *= self._expected_damage_multiplier(belief, spell.damage_type, explore = EXPLORE_WITH_SPELLS)

        kill_bonus = belief.probability_at_or_below(round(expected_damage)) * 2.0
        priority_bonus = self._priority_bonus(belief)

        if is_ally:
            return {"friendly_fire": -expected_damage}
        return {"expected_damage": expected_damage, "kill_bonus": kill_bonus, "priority_bonus": priority_bonus}