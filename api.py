from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json

from combat import monte_carlo, run_combat_live
from data import load_weapons, load_spells, load_monsters, load_players, spawn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5173"],
    allow_methods = ["*"],
    allow_headers = ["*"]
)

@app.get("/simulate")
def simulate(goblins: int = 3, hobgoblins: int = 1, n: int = 10000):
    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")

    player_registry = load_players("players.json", weapon_registry, spell_registry)
    players = [spawn(player_registry, "Fighter"), spawn(player_registry, "Cleric")]

    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)
    monsters = []

    for i in range(goblins):
        monsters.append(spawn(monster_registry, "Goblin", f"Goblin {chr(65 + i)}"))

    for i in range(hobgoblins):
        monsters.append(spawn(monster_registry, "Hobgoblin", f"Hobgoblin {chr(65 + i)}"))

    return monte_carlo(players, monsters, n, False)

@app.get("/simulate-live")
async def simulate_live(goblins: int = 3, hobgoblins: int = 1):
    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")

    player_registry = load_players("players.json", weapon_registry, spell_registry)
    players = [spawn(player_registry, "Fighter"), spawn(player_registry, "Cleric")]

    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)
    monsters = []

    for i in range(goblins):
        monsters.append(spawn(monster_registry, "Goblin", f"Goblin {chr(65 + i)}"))

    for i in range(hobgoblins):
        monsters.append(spawn(monster_registry, "Hobgoblin", f"Hobgoblin {chr(65 + i)}"))
    
    rounds = list(run_combat_live(players, monsters))
    return rounds