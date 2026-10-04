# D&D Combat Simulator — front end

React + Vite client for the combat engine's FastAPI backend.

## Running locally

Backend (from the project root):

```bash
python3 -m uvicorn api:app --port 8000
```

Front end (from `dnd-frontend`):

```bash
npm install
npm run dev
```

Open http://localhost:5173.

## Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `VITE_API_URL` | front end (build time) | `http://127.0.0.1:8000` | Base URL of the API |
| `ALLOWED_ORIGINS` | backend (runtime) | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated CORS origins |

## Views

- **Monte Carlo** — build an encounter from dropdowns (any mix of the SRD monsters, up to 12) and run 100, 200 or 500 fights per policy. All four PC policies (Random, Greedy, BeliefUpdating, Omniscient) are shown side by side with standard errors. The monsters always play Greedy.
- **Live combat** — step through one fight in each of the two named encounters (PCs on BeliefUpdating, monsters on Greedy). The decision panel shows the ranked candidate actions, what each score is made of, and the acting combatant's beliefs next to the truth. Seeds are echoed so a fight can be replayed.

## Scripts

`npm run dev`, `npm run build`, `npm run lint`.