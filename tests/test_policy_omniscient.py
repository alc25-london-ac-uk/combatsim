from belief import CombatantBelief
from policy_omniscient import OmniscientPolicy
from policy_beliefupdating import BeliefUpdatingPolicy

# --- _belief_for: the one overridden seam ---

def test_belief_for_returns_ground_truth_not_a_lazily_learned_prior(make_player, make_monster):
    attacker = make_player()
    target = make_monster(max_hp = 20)
    target.hp = 7
    policy = OmniscientPolicy()

    belief = policy._belief_for(target, {})

    assert belief.hypotheses == {(7, 20): 1.0}

def test_belief_for_does_not_populate_the_beliefs_dict(make_player, make_monster):
    attacker = make_player()
    target = make_monster()
    beliefs = {}
    policy = OmniscientPolicy()

    policy._belief_for(target, beliefs)

    assert beliefs == {}

def test_belief_for_reflects_hp_changes_immediately_with_no_memory_of_the_past(make_player, make_monster):
    target = make_monster(max_hp = 20)
    target.hp = 20
    policy = OmniscientPolicy()

    first = policy._belief_for(target, {})
    target.hp = 3
    second = policy._belief_for(target, {})

    assert first.expected_hp() == 20
    assert second.expected_hp() == 3

# --- OmniscientPolicy inherits BeliefUpdatingPolicy's scoring unchanged ---

def test_omniscient_policy_is_a_belief_updating_policy_subclass():
    assert issubclass(OmniscientPolicy, BeliefUpdatingPolicy)

def test_omniscient_policy_scores_identically_to_belief_updating_given_an_accurate_belief(make_player, make_monster, melee_weapon, make_combat_state):
    attacker = make_player()
    target = make_monster(ac = 10, max_hp = 20)
    target.hp = 20
    combat_state = make_combat_state(attacker, target)
    weapon = melee_weapon()

    omniscient = OmniscientPolicy()
    omniscient_score = omniscient.score_attack(attacker, target, weapon, combat_state, {})

    believing = BeliefUpdatingPolicy()
    accurate_beliefs = {target: CombatantBelief.ground_truth_for(target)}
    believing_score = believing.score_attack(attacker, target, weapon, combat_state, accurate_beliefs)

    assert omniscient_score == believing_score

def test_omniscient_policy_correctly_identifies_a_fully_depleted_caster(make_player, make_monster):
    caster = make_player()
    caster.spell_slots = {1: 0, 2: 0}
    policy = OmniscientPolicy()

    belief = policy._belief_for(caster, {})

    assert belief.depleted == 1.0

def test_omniscient_policy_reads_true_resistance_without_ever_observing_a_hit(make_player, make_monster):
    from enums import DamageType

    target = make_monster(damage_resistances = [DamageType.FIRE])
    policy = OmniscientPolicy()

    belief = policy._belief_for(target, {})

    assert belief.damage_multiplier(DamageType.FIRE) == 0.5
