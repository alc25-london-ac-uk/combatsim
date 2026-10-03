import math

from belief import CombatantBelief, belief_vs_truth
from enums import TargetType, Ability, DamageType
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_greedyutility import GreedyUtilityPolicy
from spell import Spell

def _damage_spell(**overrides):
    defaults = dict(
        name = "Test Bolt", level = 0, target_type = TargetType.ENEMY, damage_type = DamageType.FIRE,
        damage_dice = 2, damage_sides = 6, range = 120, requires_attack_roll = False,
        save_allowed = False, save_attribute = Ability.DEXTERITY
    )
    defaults.update(overrides)
    return Spell(**defaults)

# --- the score is the sum of its named components ---

def test_an_attack_score_is_exactly_the_sum_of_its_components(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    target = make_monster()
    weapon = melee_weapon()
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    terms = policy._attack_terms(attacker, target, weapon, combat_state, {})

    assert set(terms) == {"expected_damage", "kill_bonus", "priority_bonus", "target_priority_bonus", "movement_penalty"}
    assert policy.score_attack(attacker, target, weapon, combat_state, {}) == sum(terms.values())

def test_an_attack_that_cannot_reach_this_turn_has_a_single_approach_component(make_player, make_monster, melee_weapon):
    from world import Grid, CombatState

    attacker = make_player()
    target = make_monster()
    grid = Grid(30, 30)
    grid.place(attacker, 0, 0)
    grid.place(target, 20, 0)
    combat_state = CombatState(grid = grid, initiative_order = [attacker, target])

    terms = BeliefUpdatingPolicy()._attack_terms(attacker, target, melee_weapon(), combat_state, {})

    assert list(terms) == ["approach_penalty"] and terms["approach_penalty"] <= 0

def test_a_spell_hit_score_is_exactly_the_sum_of_its_components(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    combat_state = make_combat_state(caster, target)
    policy = BeliefUpdatingPolicy()
    spell = _damage_spell()

    terms = policy._spell_hit_terms(caster, target, spell, combat_state, {})

    assert set(terms) == {"expected_damage", "kill_bonus", "priority_bonus"}
    assert policy.score_spell_hit(caster, target, spell, combat_state, {}) == sum(terms.values())

def test_the_spell_breakdown_adds_up_to_the_spell_score(make_player, make_monster, make_combat_state):
    caster = make_player()
    target = make_monster()
    nearby = make_monster(name = "Nearby")
    combat_state = make_combat_state(caster, target, nearby) # everyone is on one square, so a burst catches both enemies
    policy = BeliefUpdatingPolicy()
    burst = _damage_spell(name = "Test Burst", aoe_radius = 20, save_allowed = True, damage_pct_on_save = 0.5)

    breakdown = policy._spell_breakdown(caster, target, burst, combat_state, {})

    assert math.isclose(sum(breakdown.values()), policy.score_spell(caster, target, burst, combat_state, {}), rel_tol = 1e-9)
    assert "movement_penalty" in breakdown

def test_damage_to_your_own_side_is_reported_as_friendly_fire_not_netted_into_expected_damage(make_player, make_monster, make_combat_state):
    caster = make_player(name = "Caster")
    ally = make_player(name = "Ally")
    enemy = make_monster(name = "Enemy")
    combat_state = make_combat_state(caster, ally, enemy) # one square, so the burst catches the enemy and both PCs
    policy = BeliefUpdatingPolicy()
    burst = _damage_spell(name = "Test Burst", aoe_radius = 20, save_allowed = True, damage_pct_on_save = 0.5)

    breakdown = policy._spell_breakdown(caster, enemy, burst, combat_state, {})
    enemy_only = policy._spell_hit_terms(caster, enemy, burst, combat_state, {})
    ally_only = policy._spell_hit_terms(caster, ally, burst, combat_state, {})

    assert breakdown["expected_damage"] == enemy_only["expected_damage"] > 0 # the enemy's damage is no longer reduced by the allies caught in the blast
    assert breakdown["friendly_fire"] < 0
    assert set(ally_only) == {"friendly_fire"}
    assert math.isclose(sum(breakdown.values()), policy.score_spell(caster, enemy, burst, combat_state, {}), rel_tol = 1e-9)

def test_a_spell_that_catches_no_allies_has_no_friendly_fire_component(make_player, make_monster, make_combat_state):
    caster = make_player()
    enemy = make_monster()
    combat_state = make_combat_state(caster, enemy)

    breakdown = BeliefUpdatingPolicy()._spell_breakdown(caster, enemy, _damage_spell(), combat_state, {})

    assert "friendly_fire" not in breakdown

def test_a_spell_without_a_slot_is_reported_as_unavailable(make_player, make_monster, make_combat_state):
    caster = make_player()
    caster.spell_slots = {}
    target = make_monster()
    combat_state = make_combat_state(caster, target)

    breakdown = BeliefUpdatingPolicy()._spell_breakdown(caster, target, _damage_spell(level = 1), combat_state, {})

    assert breakdown == {"no_spell_slot": -1.0}

# --- recording decisions ---

def test_nothing_is_recorded_unless_recording_is_switched_on(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = BeliefUpdatingPolicy()

    policy.decide(attacker, combat_state, {})

    assert policy.explanations is None and policy._candidate_log is None

def test_a_recorded_decision_lists_ranked_candidates_with_the_chosen_one_marked(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon(name = "Sword")]
    near = make_monster(name = "Near", max_hp = 10)
    far = make_monster(name = "Far", max_hp = 200)
    combat_state = make_combat_state(attacker, near, far)
    policy = BeliefUpdatingPolicy()
    policy.explanations = []

    action = policy.decide(attacker, combat_state, {})

    assert len(policy.explanations) == 1
    record = policy.explanations[0]
    totals = [c["total"] for c in record["candidates"]]
    assert totals == sorted(totals, reverse = True)
    assert record["combatant"] == attacker.name and record["bonus_action"] is False
    assert record["chosen"]["target"] == action.target.name
    assert [c for c in record["candidates"] if c["chosen"]][0]["target"] == action.target.name
    assert all(set(c) >= {"kind", "label", "target", "total", "terms", "chosen"} for c in record["candidates"])

def test_only_the_best_few_candidates_are_kept_but_the_chosen_one_always_is(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon(name = "Sword")]
    enemies = [make_monster(name = f"Enemy {i}") for i in range(9)]
    combat_state = make_combat_state(attacker, *enemies)
    policy = BeliefUpdatingPolicy()
    policy.explanations = []

    policy.decide(attacker, combat_state, {})

    candidates = policy.explanations[0]["candidates"]
    assert len(candidates) == 5 and any(c["chosen"] for c in candidates)

def test_candidates_that_can_never_be_taken_are_left_out(make_player, make_monster, make_combat_state):
    caster = make_player()
    caster.spells = [_damage_spell(name = "Needs A Slot", level = 3)]
    caster.spell_slots = {}
    target = make_monster()
    combat_state = make_combat_state(caster, target)
    policy = BeliefUpdatingPolicy()
    policy.explanations = []

    policy.decide(caster, combat_state, {})

    assert policy.explanations[0]["candidates"] == []

def test_a_recorded_decision_carries_the_actors_beliefs_about_every_living_enemy(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon()]
    alive = make_monster(name = "Alive")
    dead = make_monster(name = "Dead")
    dead.hp = 0
    ally = make_player(name = "Ally")
    combat_state = make_combat_state(attacker, ally, alive, dead)
    policy = BeliefUpdatingPolicy()
    policy.explanations = []

    policy.decide(attacker, combat_state, {})

    assert [b["name"] for b in policy.explanations[0]["beliefs"]] == ["Alive"]

def test_the_greedy_policy_records_decisions_in_the_same_way(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    attacker.weapons = [melee_weapon()]
    target = make_monster()
    combat_state = make_combat_state(attacker, target)
    policy = GreedyUtilityPolicy()
    policy.explanations = []

    policy.decide(attacker, combat_state, {})

    assert len(policy.explanations) == 1 and policy.explanations[0]["beliefs"][0]["name"] == target.name

# --- beliefs against truth ---

def test_belief_vs_truth_reports_believed_and_true_hp_and_ac(make_monster):
    monster = make_monster(ac = 17, max_hp = 40)
    belief = CombatantBelief.initial_prior_for(monster)

    summary = belief_vs_truth(belief, monster)

    assert summary["hp"]["true"] == 40 and abs(summary["hp"]["believed"] - belief.expected_hp()) < 1e-9
    assert summary["ac"]["true"] == 17 and abs(summary["ac"]["believed"] - belief.expected_armour_class()) < 1e-9

def test_belief_vs_truth_lists_every_save_with_the_true_modifier(make_monster):
    from combatant import AbilityScores

    monster = make_monster(ability_scores = AbilityScores(dexterity = 16))
    summary = belief_vs_truth(CombatantBelief.initial_prior_for(monster), monster)

    saves = {s["ability"]: s["true"] for s in summary["saves"]}
    assert len(saves) == 6 and saves["dexterity"] == 3

def test_an_untested_resistance_shows_as_unknown_while_a_tested_one_shows_what_was_learned(make_monster):
    monster = make_monster()
    monster.damage_resistances = [DamageType.FIRE]
    monster.damage_vulnerabilities = [DamageType.COLD]
    belief = CombatantBelief.initial_prior_for(monster)
    belief.observe_damage_mitigation(DamageType.COLD, expected_damage = 10, actual_damage = 20)

    rows = {r["type"]: r for r in belief_vs_truth(belief, monster)["damage_types"]}

    assert rows["fire"]["believed"] is None and rows["fire"]["true"] == 0.5 # resistance not yet discovered
    assert rows["cold"]["believed"] is not None and rows["cold"]["true"] == 2.0

def test_a_tested_damage_type_with_nothing_special_is_listed_with_its_learned_value(make_monster):
    monster = make_monster()
    belief = CombatantBelief.initial_prior_for(monster)
    belief.observe_damage_mitigation(DamageType.SLASHING, expected_damage = 10, actual_damage = 10)

    rows = {r["type"]: r for r in belief_vs_truth(belief, monster)["damage_types"]}

    assert rows["slashing"] == {"type": "slashing", "believed": 1.0, "true": 1.0}
    assert "fire" not in rows # untested and ordinary: nothing to show

def test_belief_vs_truth_compares_caster_flags_to_the_real_spell_list(make_monster):
    healer = make_monster(name = "Healer")
    healer.spells = [Spell(
        name = "Mend", level = 0, target_type = TargetType.ALLY, damage_type = None, damage_dice = 1, damage_sides = 8,
        range = 5, requires_attack_roll = False, save_allowed = False, save_attribute = Ability.WISDOM, is_healing = True
    )]
    belief = CombatantBelief.initial_prior_for(healer)

    flags = belief_vs_truth(belief, healer)["flags"]

    assert flags["healer"] == {"believed": 0.5, "true": True}
    assert flags["offensive_caster"]["true"] is False

def test_slot_depletion_is_not_applicable_to_a_creature_with_no_spell_slots(make_monster):
    fighter = make_monster(name = "Brute")
    caster = make_monster(name = "Caster")
    caster.spell_slots = {1: 2}
    caster.max_spell_slots = {1: 2}

    assert belief_vs_truth(CombatantBelief.initial_prior_for(fighter), fighter)["flags"]["slots_depleted"]["true"] is None
    assert belief_vs_truth(CombatantBelief.initial_prior_for(caster), caster)["flags"]["slots_depleted"]["true"] is False
