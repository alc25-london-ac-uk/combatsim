# Probabilistic AI for a D&D Combat Simulator

A grid-based D&D 5e combat engine and a family of decision-making agents.
Four policies play the party (four level-5 characters: two Fighters, a Cleric and a Wizard) against a monster team that always plays the Greedy policy:

| Policy | What it knows about hidden enemy state (HP, AC, saving throws, resistances, caster flags) |
|---|---|
| `Random` | nothing; picks any legal action (the floor) |
| `Greedy` | fixed, class-typical guesses that are never updated (the baseline) |
| `BeliefUpdating` | starts from the same guesses and updates them from what it observes, with likelihood-ratio Bayesian updates (the hypothesis) |
| `Omniscient` | the ground truth (the upper bound) |

## Running it

Python 3.14. Install `requirements-dev.txt` (the API needs only `requirements.txt`).

```bash
python3 -m pytest                                          # the test suite
python3 evaluation.py --fights 10000 --seed 2024           # PC win rate for each policy in each named encounter
python3 agreement.py --fights 1000 --seed 2024             # how often each policy picks Omniscient's action
python3 cr_difficulty.py                                   # the official CR difficulty tier of each named encounter
python3 -m uvicorn api:app --port 8000                     # the API
cd dnd-frontend && npm install && npm run dev              # the front end (http://localhost:5173)
docker build -t combatsim-api .                            # the API as a container
```

Results are deterministic for a given base seed (each configuration derives its own seed from it). The saved output of the final run is in `results/`.