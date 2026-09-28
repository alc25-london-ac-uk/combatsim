import random

from enums import AttackResult, ActionType
from combatant import Combatant
from ai import ActionResult
from world import CombatState, Grid

def log_action(combatant: Combatant, results: list[ActionResult]) -> list[str]:
    log = []
    for result in results:
        match result.action_type:
            case ActionType.MOVE:
                log.append(f"{combatant.name} moved to {result.combatant_x},{result.combatant_y}")
            case ActionType.SPELL:
                log.append(format_spell_result(combatant, result))
                log.append(f" -> {result.rationale}")
            case ActionType.ATTACK:
                log.append(format_attack_result(combatant, result))
                log.append(f" -> {result.rationale}")
            case ActionType.NONE:
                log.append(f"{combatant.name} skipped their turn.")
    return log

def format_attack_result(combatant: Combatant, result: ActionResult) -> str:
    prefix = f"{result.actor} attacks {result.target.name} with {result.weapon} - "

    if result.attack_result != AttackResult.MISS:
        return f"{prefix}{result.amount} damage. {result.target.name} has {result.target_hp_after_action} HP remaining."
    else:
        return f"{prefix}miss."

def format_spell_result(combatant: Combatant, result: ActionResult) -> str:
    prefix = f"{result.actor} casts {result.spell} on {result.target.name} - "

    # healing spells
    if result.is_healing:
        return f"{prefix}heals {result.amount}. {result.target.name} has {result.target_hp_after_action} HP remaining."
    
    # control spells
    if result.amount == 0:
        if result.effect_applied:
            return f"{prefix}{result.effect_applied} applied."

        if result.save_made:
            return f"{prefix}save succeeded; no effect."

    # damage spells
    if result.attack_result != AttackResult.MISS:
        suffix = f" {result.effect_applied} applied." if result.effect_applied else ""
        return f"{prefix}{result.amount} damage. {result.target.name} has {result.target_hp_after_action} HP remaining.{suffix}"

    return f"{prefix}miss."

def run_combat_live(party: list[Combatant], enemies: list[Combatant]):
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

    def snapshot(log_lines, winner = None):
        return {
            "log": log_lines,
            "positions": [
                {
                    "name": c.name,
                    "team": c.team,
                    "hp": c.hp,
                    "max_hp": c.max_hp,
                    "x": combat_state.grid.position_of(c).x,
                    "y": combat_state.grid.position_of(c).y,
                    "alive": c.alive
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

            results = combatant.ai.take_turn(combat_state)

            combatant.end_turn()

            log_lines = log_action(combatant, results)

            # update beliefs
        
            party_alive = any(c.alive for c in party)
            enemies_alive = any(c.alive for c in enemies)

            if (not enemies_alive and not party_alive) or round_num > 50:
                winner = "draw"
            elif not enemies_alive:
                winner = "party"
            elif not party_alive:
                winner = "enemies"
        
            yield(snapshot(log_lines, winner))

            if winner:
                return

def run_combat(party: list[Combatant], enemies: list[Combatant], log: bool = False) -> str:
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

            if log:
                for log_line in log_action(combatant, results):
                    print(log_line)

            # update beliefs
        
        party_alive = any(c.alive for c in party)
        enemies_alive = any(c.alive for c in enemies)

        if log:
            print()

        if (not enemies_alive and not party_alive) or round_num > 50:
            return "draw"
        if not enemies_alive:
            return "party"
        if not party_alive:
            return "enemies"
        
def monte_carlo(party: list[Combatant], enemies: list[Combatant], n: int = 10000, log: bool = False) -> dict:
    results = {"party": 0, "enemies": 0, "draw": 0}

    for _ in range(n):
        winner = run_combat(party, enemies, log)
        results[winner] += 1

    return {
        "party_win_pct": results["party"] / n * 100,
        "enemy_win_pct": results["enemies"] / n * 100,
        "draw_pct": results["draw"] / n * 100,
        "n": n
    }