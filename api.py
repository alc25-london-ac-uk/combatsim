import os
import random
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from combat import monte_carlo, run_combat_live
from cr_difficulty import adjusted_encounter_xp, classify_difficulty
from data import load_weapons, load_spells, load_players, load_monsters
from evaluation import win_rate_standard_error
from parallel import run_jobs_in_parallel
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_greedyutility import GreedyUtilityPolicy
from scenarios import POLICIES, ENCOUNTERS, build_party, build_monsters, build_encounter

DATA_DIRECTORY = Path(__file__).resolve().parent

MAX_MONSTERS = 12 # limits on what one request may ask for, so a hosted server cannot be tied up
MAX_RUNS = 500
SIMULATE_WORKERS = int(os.environ.get("SIMULATE_WORKERS", 4)) # one process per policy; set lower on small hosts

weapon_registry = load_weapons(str(DATA_DIRECTORY / "weapons.json"))
spell_registry = load_spells(str(DATA_DIRECTORY / "spells.json"))
player_registry = load_players(str(DATA_DIRECTORY / "players.json"), weapon_registry, spell_registry)
monster_registry = load_monsters(str(DATA_DIRECTORY / "monsters.json"), weapon_registry, spell_registry)

app = FastAPI(title = "Combat simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods = ["GET", "POST"],
    allow_headers = ["*"]
)

app.add_middleware(GZipMiddleware, minimum_size = 1000)

class MonsterCount(BaseModel):
    name: str
    count: int = Field(ge = 1, le = MAX_MONSTERS)

class SimulateRequest(BaseModel):
    monsters: list[MonsterCount] = Field(min_length = 1)
    runs: int = Field(default = 100, ge = 1, le = MAX_RUNS)
    seed: Optional[int] = None

class LiveRequest(BaseModel):
    encounter: str
    seed: Optional[int] = None

def _expand(monsters: list[MonsterCount]) -> list[str]:
    unknown = sorted({m.name for m in monsters if m.name not in monster_registry})
    if unknown:
        raise HTTPException(status_code = 422, detail = f"Unknown monster(s): {', '.join(unknown)}")

    names = [m.name for m in monsters for _ in range(m.count)]
    if len(names) > MAX_MONSTERS:
        raise HTTPException(status_code = 422, detail = f"An encounter can have at most {MAX_MONSTERS} monsters (asked for {len(names)})")
    return names

def _simulate_policy(job: tuple) -> dict:
    monster_names, policy_name, runs, seed = job
    if seed is not None:
        random.seed(seed)

    party = build_party(player_registry, POLICIES[policy_name]())
    enemies = build_monsters(monster_names, monster_registry, GreedyUtilityPolicy())
    return monte_carlo(party, enemies, runs, False)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/monsters")
def monsters():
    def names(damage_types):
        return [d.name.lower() for d in damage_types]

    rows = [
        {
            "name": name,
            "cr": monster.challenge_rating,
            "hp": monster.max_hp,
            "ac": monster.ac,
            "vulnerabilities": names(monster.damage_vulnerabilities),
            "resistances": names(monster.damage_resistances),
            "immunities": names(monster.damage_immunities),
            "spells": [spell.name for spell in monster.spells],
            "attacks": [weapon.name for weapon in monster.weapons],
        }
        for name, monster in monster_registry.items()
    ]
    return sorted(rows, key = lambda row: (row["cr"], row["name"]))

@app.get("/encounters")
def encounters():
    party = build_party(player_registry)
    rows = []
    for encounter_id, monster_names in ENCOUNTERS.items():
        counts: dict[str, int] = {}
        for name in monster_names:
            counts[name] = counts.get(name, 0) + 1
        rows.append({
            "id": encounter_id,
            "title": encounter_id.replace("_", " ").capitalize(),
            "monsters": [{"name": name, "count": count} for name, count in counts.items()],
            "monster_count": len(monster_names),
            "adjusted_xp": adjusted_encounter_xp(monster_names, monster_registry),
            "cr_tier": classify_difficulty(monster_names, monster_registry, party),
        })
    return rows

@app.post("/simulate")
def simulate(request: SimulateRequest):
    """Run the chosen encounter many times with each of the four policies on the PCs' side; the monsters always play Greedy."""
    monster_names = _expand(request.monsters)
    jobs = [
        (monster_names, policy_name, request.runs, None if request.seed is None else request.seed + index)
        for index, policy_name in enumerate(POLICIES)
    ]
    results = run_jobs_in_parallel(_simulate_policy, jobs, SIMULATE_WORKERS)

    return {
        "runs": request.runs,
        "monster_count": len(monster_names),
        "seed": request.seed,
        "results": [
            {
                "policy": policy_name,
                "pc_win_pct": result["party_win_pct"],
                "pc_win_se": win_rate_standard_error(result["party_win_pct"], result["n"]),
                "monster_win_pct": result["enemy_win_pct"],
                "draw_pct": result["draw_pct"],
                "average_rounds": result["average_rounds"],
                "n": result["n"],
            }
            for policy_name, result in zip(POLICIES, results)
        ],
    }

_live_lock = threading.Lock() # the fight draws from the global random generator; one at a time keeps a seed replayable

@app.post("/simulate-live")
def simulate_live(request: LiveRequest):
    """One fight in a named encounter: PCs use BeliefUpdating, monsters use Greedy, and every decision is explained."""
    if request.encounter not in ENCOUNTERS:
        raise HTTPException(status_code = 404, detail = f"Unknown encounter: {request.encounter}")

    seed = request.seed if request.seed is not None else random.SystemRandom().randrange(1_000_000)

    with _live_lock:
        random.seed(seed)
        party = build_party(player_registry, BeliefUpdatingPolicy())
        enemies = build_encounter(request.encounter, monster_registry, GreedyUtilityPolicy())
        frames = list(run_combat_live(party, enemies, explain = True))

    return {"encounter": request.encounter, "seed": seed, "frames": frames}