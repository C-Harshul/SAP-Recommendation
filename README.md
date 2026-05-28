# SAP Experience Garage — Recommendation Platform

End-to-end stack for turning **user interviews**, **community signals**, and **market trends** into ranked SAP Experience Garage mission ideas — with a dashboard, Kanban board, and Gmail newsletter delivery.

| Component | Path | Role |
|-----------|------|------|
| **Dashboard** | [`frontend/`](frontend/) | React UI (Overview, Ranked Ideas, Mission Board, AI Insights) |
| **Recommendation engine** | [`recommendation_engine/`](recommendation_engine/) | LangGraph pipeline + FastAPI backend |
| **Market trends** | [`Market_trends/`](Market_trends/) | Bronze ingestion (S3) + Databricks silver/gold enrichment |

---

## Architecture

```
Market_trends (ingestion)  →  S3 bronze / Databricks silver & gold
Interviews & community     →  S3 bronze
                    │
                    ▼
        recommendation_engine (LangGraph)
        extract → synthesize → cluster → rank → writeup → persist
                    │
                    ▼
        frontend (rec-pilot-dash)  ←→  FastAPI (:8000)
```

---

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS credentials for S3 (`market-trend-exp2` or your bucket)
- Google API key (Gemini) for LLM stages
- Optional: Databricks token for embeddings; Gmail OAuth for newsletter

### 1. Environment

Copy and fill secrets at the repo root (never commit `.env`):

```bash
cp recommendation_engine/.env.example .env
# Edit: GOOGLE_API_KEY, AWS_PROFILE, EG_S3_BUCKET, etc.
```

### 2. Backend API

```bash
cd recommendation_engine
python -m venv .venv && source .venv/bin/activate
pip install -e .
eg-api
```

Runs at `http://127.0.0.1:8000`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:8080` (Vite proxies `/api` to the backend).

### 4. Run ranking

In the UI, click **Run Ranking**, or:

```bash
curl -X POST http://127.0.0.1:8000/api/pipeline/run
```

Results appear under **Ranked Ideas**, **Mission Board**, and **AI Insights** when the pipeline completes.

---

## Features

| Feature | Description |
|---------|-------------|
| **Ranking pipeline** | LangGraph job over S3 interviews, community, and trend signals |
| **Pipeline cache** | Skips full re-run when inputs + config are unchanged (`.eg_cache/`) |
| **Mission Board** | Kanban (Ideation → Backlog → Analysis → Prototype); drag-and-drop persisted |
| **AI Insights** | Newsletter-style preview; row click opens full markdown writeup |
| **Gmail newsletter** | OAuth in UI; sends ranked ideas as HTML email (`SAP Experience garage ideas`) |

---

## Market trends ingestion

Bronze pulls external feeds into S3; Databricks builds LLM-ready silver tables.

```bash
cd Market_trends/ingestion
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m ingestion.main run --all
```

See [`Market_trends/README.md`](Market_trends/README.md) and [`Market_trends/RUNBOOK.md`](Market_trends/RUNBOOK.md).

---

## API overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/pipeline/run` | POST | Start ranking run |
| `/api/pipeline/status` | GET | Run progress |
| `/api/missions/ranked` | GET | Top missions for UI |
| `/api/kanban/missions/{id}` | PATCH | Update mission stage |
| `/api/newsletter/oauth/start` | POST | Start Gmail OAuth |
| `/api/newsletter/send` | POST | Email ranked ideas |

Full details: [`recommendation_engine/README.md`](recommendation_engine/README.md).

---

## Configuration (common)

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Gemini for extract / rank / writeup |
| `AWS_PROFILE` | S3 read/write |
| `EG_S3_BUCKET` | Data bucket (default `market-trend-exp2`) |
| `EG_PIPELINE_CACHE` | Disk cache for pipeline snapshots |
| `EG_PIPELINE_RESULTS_S3` | Upload snapshots to `bronze/gold/pipeline_runs/` |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` | Newsletter OAuth |
| `EG_NEWSLETTER_DEFAULT_TO` | Default recipient email |

---

## Repository layout

```
DAPL/
├── .env                    # Local secrets (gitignored)
├── frontend/               # React dashboard
├── recommendation_engine/  # LangGraph + FastAPI
└── Market_trends/          # Ingestion + Databricks pipelines
```

---

## Further reading

- [Recommendation engine](recommendation_engine/README.md) — graph nodes, scoring, cache, CLI
- [Frontend](frontend/README.md) — dev server and proxy
- [Market trends](Market_trends/README.md) — ingestion and Databricks flow

---

## License

Internal SAP Experience Garage project. Adjust licensing as required by your organization.
