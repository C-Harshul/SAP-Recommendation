# rec-pilot-dash (Experience Garage)

Copy of [rec-pilot-dash](https://github.com/C-Harshul/rec-pilot-dash) wired to the DAPL `recommendation_engine` backend.

## Run locally

**1. API (from repo root, with `DAPL/.env` configured):**

```bash
cd recommendation_engine
source .venv/bin/activate
pip install -e ".[dev]"   # if fastapi/uvicorn not installed yet
eg-api
# or: python -m recommendation_engine.api.server
```

API listens on `http://127.0.0.1:8000`.

**2. Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:8080`. Vite proxies `/api` → `http://127.0.0.1:8000`.

## Run Ranking

Use **Run Ranking** in the top bar. That calls `POST /api/pipeline/run`, which:

1. Loads interviews, community, and market trends from S3 (per `.env`)
2. Runs the LangGraph pipeline (extract → rank → writeup)
3. Exposes results at `GET /api/missions/ranked`

The UI polls status until complete, then refreshes Ranked Ideas / Overview / Pipeline.

No placeholder missions are shown — only engine output after a successful run. Interviews & market trends come from S3; community can use `EG_COMMUNITY_SOURCE=fixtures` (hardcoded `mock_community.json`). Set `EG_ALLOW_FIXTURES=0`.

## Environment

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE` | Optional API prefix (default: use Vite proxy) |
| `VITE_API_PROXY_TARGET` | Proxy target (default `http://127.0.0.1:8000`) |
| `EG_API_PORT` | API port (default `8000`) |

Backend uses the same `DAPL/.env` as the CLI (`GOOGLE_API_KEY`, `AWS_PROFILE`, `EG_DATA_SOURCE`, etc.).
