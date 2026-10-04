import random

from enums import AttackResult, ActionType
from combatant import Combatant
from ai import ActionResult
from world import CombatState, Grid
from belief import CombatantBelief, belief_for

def log_action(combatant: Combatant, results: list[ActionResult]) -> list[str]:
    # a turn that produced nothing but "no action" results (no moves, attacks or spells) is a skipped turn
    if results and all(result.action_type == ActionType.NONE for result in results):
        return [format_skipped_turn(combatant, results[0])]

    log = []
    index = 0
    while index < len(results):
        end = end_of_run(results, index)
        run = results[index:end]
        index = end

        match run[0].action_type:
            case ActionType.MOVE:
                log.append(format_movement(combatant, run))
            case ActionType.SPELL:
                log.extend(format_spell_cast(combatant, run))
                log.append(f" -> {run[0].rationale}")
            case ActionType.ATTACK:
                log.append(format_attack_result(combatant, run[0]))
                log.append(f" -> {run[0].rationale}")
            case ActionType.BREAK_FREE:
                log.append(format_struggle(run[0]))
    return log

def end_of_run(results: list[ActionResult], start: int) -> int:
    # index just past the results that belong on one log entry: consecutive moves, or the hits of a single spell cast
    first = results[start]
    end = start + 1
    while end < len(results) and belongs_with(first, results[end]):
        end += 1
    return end

def belongs_with(first: ActionResult, other: ActionResult) -> bool:
    if first.action_type == ActionType.MOVE:
        return other.action_type == ActionType.MOVE
    if first.action_type == ActionType.SPELL:
        return other.action_type == ActionType.SPELL and other.actor == first.actor and other.spell == first.spell
    return False

def broadcast_observations(actor: Combatant, results: list[ActionResult], combat_state: CombatState) -> None:
    cast_offensive = any(r.action_type == ActionType.SPELL and not r.is_healing for r in results)
    cast_healing = any(r.action_type == ActionType.SPELL and r.is_healing for r in results)
    cast_concentration = any(r.action_type == ActionType.SPELL and r.concentration for r in results)
    leveled_spells_cast = {r.spell for r in results if r.action_type == ActionType.SPELL and r.spell_level > 0}

    if cast_offensive or cast_healing or cast_concentration or leveled_spells_cast:
        for observer in combat_state.initiative_order:
            if observer is actor or observer.ai is None:
                continue

            belief = belief_for(observer.ai.beliefs, actor)
            if cast_offensive:
                belief.observe_offensive_cast()
            if cast_healing:
                belief.observe_healing_cast()
            if cast_concentration:
                belief.observe_concentration_spell_cast()
            for _ in leveled_spells_cast:
                belief.observe_leveled_spell_cast()

    for result in results:
        if result.action_type not in (ActionType.ATTACK, ActionType.SPELL):
            continue

        observe_defences(actor, result, combat_state)

        if result.amount <= 0:
            continue

        target = result.target
        for observer in combat_state.initiative_order:
            if observer is target or observer.ai is None:
                continue

            belief = belief_for(observer.ai.beliefs, target)
            if result.is_healing:
                belief.observe_healing(result.amount)
            else:
                if result.mitigated_amount > 0:
                    belief.observe_damage(result.mitigated_amount)
                if result.damage_type is not None:
                    belief.observe_damage_mitigation(result.damage_type, result.amount, result.mitigated_amount)

def observe_defences(actor: Combatant, result: ActionResult, combat_state: CombatState) -> None:
    learns_attack_outcome = result.attack_roll_bonus is not None and result.attack_result != AttackResult.CRIT
    learns_save_outcome = result.save_ability is not None and result.save_dc is not None and result.save_succeeded is not None
    if not (learns_attack_outcome or learns_save_outcome):
        return

    # Attack bonuses and save DCs are only treated as known to the acting side, so only teammates of the actor learn the target's defences.
    for observer in combat_state.initiative_order:
        if observer is result.target or observer.team != actor.team or observer.ai is None:
            continue

        belief = belief_for(observer.ai.beliefs, result.target)
        if learns_attack_outcome:
            belief.observe_attack_roll(result.attack_roll_bonus, result.attack_result == AttackResult.HIT)
        if learns_save_outcome:
            belief.observe_save(result.save_ability, result.save_dc, result.save_succeeded)

def format_hp_after(result: ActionResult) -> str:
    # HP can drop below zero; a combatant at zero or less is simply dead
    if result.target_hp_after_action <= 0:
        return f"{result.target.name} is dead."

    return f"{result.target.name} has {result.target_hp_after_action} HP remaining."

def format_attack_result(combatant: Combatant, result: ActionResult) -> str:
    verb = "makes an opportunity attack on" if result.opportunity_attack else "attacks"
    prefix = f"{result.actor} {verb} {result.target.name} with {result.weapon} - "

    if result.attack_result != AttackResult.MISS:
        return f"{prefix}{result.amount} damage. {format_hp_after(result)}"
    else:
        return f"{prefix}miss."

def format_movement(combatant: Combatant, moves: list[ActionResult]) -> str:
    destination = moves[-1]
    line = f"{combatant.name} moved to {destination.combatant_x},{destination.combatant_y}"

    if len(moves) > 1:
        squares_passed = ", ".join(f"{move.combatant_x},{move.combatant_y}" for move in moves[:-1])
        line += f" (via {squares_passed})"

    return line

def format_struggle(result: ActionResult) -> str:
    outcome = "breaks free." if result.save_succeeded else "and fails."
    return f"{result.actor} struggles against {result.effect_applied} - {outcome}"

def format_skipped_turn(combatant: Combatant, result: ActionResult) -> str:
    # a turn lost to an effect such as Paralysed carries the effect's name as its rationale
    if result.rationale:
        return f"{combatant.name} is {result.rationale.lower()} and loses their turn."

    return f"{combatant.name} skipped their turn."

def format_spell_outcome(result: ActionResult) -> str:
    # healing spells
    if result.is_healing:
        return f"heals {result.amount}. {format_hp_after(result)}"

    # control spells
    if result.amount == 0:
        if result.effect_applied:
            return f"{result.effect_applied} applied."

        if result.save_made:
            return "save succeeded; no effect."

    # damage spells
    if result.attack_result != AttackResult.MISS:
        suffix = f" {result.effect_applied} applied." if result.effect_applied else ""
        return f"{result.amount} damage. {format_hp_after(result)}{suffix}"

    return "miss."

def format_spell_result(combatant: Combatant, result: ActionResult) -> str:
    return f"{result.actor} casts {result.spell} on {result.target.name} - {format_spell_outcome(result)}"

def format_spell_cast(combatant: Combatant, hits: list[ActionResult]) -> list[str]:
    if len(hits) == 1:
        return [format_spell_result(combatant, hits[0])]

    # one cast that hit several times (e.g. Fireball, Scorching Ray): one heading, then an indented line per hit
    lines = [f"{hits[0].actor} casts {hits[0].spell}:"]
    lines.extend(f"  {hit.target.name} - {format_spell_outcome(hit)}" for hit in hits)
    return lines

def run_combat_live(party: list[Combatant], enemies: list[Combatant], explain: bool = False):
    combat_state = CombatState(
        grid = Grid(10, 10),
        initiative_order = sorted(party + enemies,
                                  key= lambda c: c.roll_initiative(),
                                  reverse = True)
    )
    
    for p in party:
        combat_state.grid.place(p, random.randint(0, 9), 0)
    for e in enemies:
        combat_state.grid.place(e, random.randint(0, 9), 9)

    for c in combat_state.initiative_order:
        c.reset()

    def snapshot(log_lines, winner = None, decisions = None, actor = None):
        return {
            "round": round_num,
            "actor": actor, # whose turn the log lines are; None for a round heading
            "log": log_lines,
            "winner": winner,
            "decisions": decisions or [],
            "positions": [
                {
                    "name": c.name,
                    "team": c.team,
                    "hp": c.hp,
                    "max_hp": c.max_hp,
                    "x": combat_state.grid.position_of(c).x,
                    "y": combat_state.grid.position_of(c).y,
                    "alive": c.alive,
                    "spell_slots": {str(level): count for level, count in c.spell_slots.items() if c.max_spell_slots.get(level, 0) > 0},
                    "max_spell_slots": {str(level): count for level, count in c.max_spell_slots.items() if count > 0},
                    "effects": [e.name for e in c.effects]
                }
                for c in combat_state.initiative_order
            ]
        }

    round_num = 0
    winner = None

    while True:
        round_num += 1
        yield snapshot([f"--- Round {round_num} ---"])

        for combatant in combat_state.initiative_order:
            # skip turn if dead
            if not combatant.alive:
                continue

            if combatant.ai is None:
                continue

            # tick conditions
            combatant.start_turn()

            policy = combatant.ai.policy
            recording = explain and hasattr(policy, "explanations")
            if recording:
                policy.explanations = []
            try:
                results = combatant.ai.take_turn(combat_state)
                decisions = policy.explanations if recording else []
            finally:
                if recording:
                    policy.explanations = None

            combatant.end_turn()

            broadcast_observations(combatant, results, combat_state)

            log_lines = log_action(combatant, results)

            party_alive = any(c.alive for c in party)
            enemies_alive = any(c.alive for c in enemies)

            if (not enemies_alive and not party_alive) or round_num > 50:
                winner = "draw"
            elif not enemies_alive:
                winner = "party"
            elif not party_alive:
                winner = "enemies"
        
            yield(snapshot(log_lines, winner, decisions, combatant.name))

            if winner:
                return

def run_combat(party: list[Combatant], enemies: list[Combatant], log: bool = False) -> tuple[str, int]:
    combat_state = CombatState(
        grid = Grid(10, 10),
        initiative_order = sorted(party + enemies,
                                  key= lambda c: c.roll_initiative(),
                                  reverse = True)
    )
    
    for p in party:
        combat_state.grid.place(p, random.randint(0, 9), 0)
    for e in enemies:
        combat_state.grid.place(e, random.randint(0, 9), 9)

    for c in combat_state.initiative_order:
        c.reset()
    
    if log:
        print()

    round_num = 0
    while True:
        round_num += 1
        if log:
            print(f"Round {round_num}")
            print(f"-------")

        for combatant in combat_state.initiative_order:
            
            # skip turn if dead
            if not combatant.alive:
                if log:
                    print(f"{combatant.name} is dead - skipping turn.")
                continue

            if combatant.ai is None:
                continue

            # tick conditions
            combatant.start_turn()

            results = combatant.ai.take_turn(combat_state)

            combatant.end_turn()

            broadcast_observations(combatant, results, combat_state)

            if log:
                print(f"{combatant.name}'s turn")
                for log_line in log_action(combatant, results):
                    print(f"  {log_line}")
        
        party_alive = any(c.alive for c in party)
        enemies_alive = any(c.alive for c in enemies)

        if log:
            print()

        if (not enemies_alive and not party_alive) or round_num > 50:
            return "draw", round_num
        if not enemies_alive:
            return "party", round_num
        if not party_alive:
            return "enemies", round_num

def monte_carlo(party: list[Combatant], enemies: list[Combatant], n: int = 10000, log: bool = False) -> dict:
    results = {"party": 0, "enemies": 0, "draw": 0}
    total_rounds = 0

    for _ in range(n):
        winner, round_num = run_combat(party, enemies, log)
        results[winner] += 1
        total_rounds += round_num

    return {
        "party_win_pct": results["party"] / n * 100,
        "enemy_win_pct": results["enemies"] / n * 100,
        "draw_pct": results["draw"] / n * 100,
        "average_rounds": total_rounds / n,
        "n": n
    }