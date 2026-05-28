# Market Trends

Collects external AI and builder signals for the SAP Experience Garage, stores them in S3, and enriches them into queryable silver tables for downstream LLM work (including the [recommendation engine](../recommendation_engine/README.md)).

---

## What this repo does

| Layer | Where | What happens |
|-------|--------|----------------|
| **Bronze** | `ingestion/` | Python connectors pull RSS, APIs, and feeds → gzip JSONL on S3 |
| **Silver** | `databricks/` | DLT pipeline fetches article bodies, dedupes, exposes LLM-ready rows |
| **Gold** | `databricks/` | `ai_summarize` per article + mission brief via `ai_query` |

Bronze is the immutable raw archive. Silver adds full text (`body_text`) so models see content, not just URLs.

---

## End-to-end flow

```
External sources (RSS, Kaggle, HN, …)
        │
        ▼
┌───────────────────┐
│  ingestion/       │  ECS / local CLI
│  Python 3.11      │
└─────────┬─────────┘
          │  gzip JSONL
          ▼
   s3://{bucket}/bronze/{category}/{source_id}/dt=YYYY-MM-DD/…
          │
          ▼
┌───────────────────┐
│  databricks/      │  DLT + trafilatura
│  silver pipeline  │
└─────────┬─────────┘
          │
          ▼
   market-trends-exp.experience_garage_dev.silver_market_content_for_llm
          │
          ▼
   gold_market_trend_summaries + gold_mission_brief (ai_summarize / ai_query)
          │
          ▼
   gold.trend_signals (recommendation engine) → recommendation engine
```

Default bucket in docs: `market-trend-exp2`. Override via `EG_S3_BUCKET` / bundle vars.

---

## Repo layout

| Path | Read this for… |
|------|----------------|
| [`ingestion/`](ingestion/) | Connectors, CLI, Docker, bronze S3 writes, adding sources |
| [`databricks/`](databricks/) | DLT pipeline, Unity Catalog tables, article fetch |
| [`RUNBOOK.md`](RUNBOOK.md) | AWS IAM, bucket policy, first-time S3 + Databricks setup |

---

## Signal sources (three categories)

| Category | Examples | Why we track it |
|----------|----------|-----------------|
| **Builder** | Kaggle, HackerRank, Coursera, Udemy | Skills and project patterns gaining traction |
| **News** | TechCrunch, HN, arXiv, Product Hunt, Hugging Face | Funding, launches, frontier-lab news |
| **Learning** | Pluralsight, O’Reilly, LinkedIn Learning | Edtech product direction (not full catalogs) |

Each source implements a shared `BaseConnector` and is configured in `ingestion/src/ingestion/config/sources.yaml`.

---

## Bronze record (every source)

All connectors write the same envelope:

```json
{
  "source_id": "techcrunch_ai",
  "category": "news",
  "ingested_at": "2026-05-20T10:00:00Z",
  "source_published_at": "2026-05-19T14:32:00Z",
  "source_url": "https://example.com/article",
  "external_id": "stable-id-from-feed",
  "raw": { "title": "…", "summary": "…" }
}
```

**S3 path pattern:**

```
s3://{bucket}/bronze/{category}/{source_id}/dt=YYYY-MM-DD/run_{timestamp}.jsonl.gz
```

State and dead-letter queues live under `bronze/_state/` and `bronze/_dlq/`.

---

## Quick start

### 1. Bronze ingestion (local)

```bash
cd ingestion
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Set AWS_PROFILE and EG_S3_BUCKET=market-trend-exp2

python scripts/aws_whoami.py          # confirm IAM identity
python -m ingestion.main run --source techcrunch_ai
python -m ingestion.main run --all    # all configured sources
```

Use **LocalStack** for offline S3: see [`ingestion/README.md`](ingestion/README.md).

### 2. Silver enrichment (Databricks)

If UC external location on S3 is not ready, sync bronze to a UC Volume first:

```bash
./ingestion/scripts/sync_bronze_s3_to_volume.sh
```

```bash
cd databricks
databricks auth login --host https://YOUR_WORKSPACE
databricks bundle deploy -t dev
databricks bundle run market_trends_content_pipeline -t dev \
  --var bronze_s3_path=dbfs:/Volumes/market-trends-exp/experience_garage_dev/bronze
```

### 3. Gold LLM summaries

```bash
databricks bundle run market_trends_llm_insights -t dev
```

Query summaries + mission brief:

```sql
SELECT source_id, source_url, article_summary
FROM `market-trends-exp`.experience_garage_dev.gold_market_trend_summaries
ORDER BY source_published_at DESC LIMIT 20;

SELECT mission_brief FROM `market-trends-exp`.experience_garage_dev.gold_mission_brief;
```

Query silver (parsed article text):

```sql
SELECT source_id, source_url, feed_summary, body_text, source_published_at
FROM `market-trends-exp`.experience_garage_dev.silver_market_content_for_llm
ORDER BY source_published_at DESC NULLS LAST
LIMIT 50;
```

More detail: [`databricks/README.md`](databricks/README.md) and [`databricks/SETUP.md`](databricks/SETUP.md).

---

## Silver tables (Unity Catalog)

| Table | Purpose |
|-------|---------|
| `bronze_market_trends` | Streaming load of bronze JSONL |
| `silver_market_content` | Deduped rows + fetched `body_text` |
| `silver_market_content_for_llm` | Rows with usable text for prompts |
| `gold_market_trend_summaries` | Per-article `ai_summarize` output + `source_url` |
| `gold_mission_brief` | Synthesized themes / workshop ideas from recent summaries |

`content_fetch_status` values: `ok`, `http_error`, `empty_extract`, `error`, `no_url`, `skipped`. On failure the pipeline falls back to RSS summary from `raw`.

---

## How this connects to the recommendation engine

| Market Trends output | Recommendation engine input |
|----------------------|----------------------------|
| Bronze / silver content | Continuous enrichment → `gold.trend_signals` |
| Themes, momentum, URLs | `match_trends_node` validates user ideas |
| `body_text` + summaries | Industry context in mission write-ups |

Interviews and community posts are **separate** bronze paths (`bronze/interviews/`, `bronze/community/`) — owned by other pipelines, consumed by the recommendation engine.

---

## Operations checklist

1. **AWS** — Named profile with S3 access; bucket policy allows your principal ([`RUNBOOK.md`](RUNBOOK.md) Step 0–1).
2. **Ingest** — Run connectors on schedule (ECS + EventBridge in prod).
3. **Databricks** — External location + pipeline run after bronze lands.
4. **Gold LLM** — `databricks bundle run market_trends_llm_insights -t dev`
5. **Recommend** — Weekly LangGraph job in [`../recommendation_engine/`](../recommendation_engine/).

---

## Out of scope (this repo)

- Interview and community ingestion
- `gold.trend_signals` in recommendation engine (separate repo; consumes market trends gold)
- FastAPI / BTP frontend
- Weekly mission ranking (see recommendation engine)

---

## Further reading

- [`ingestion/README.md`](ingestion/README.md) — env vars, new connectors, CLI, deployment
- [`databricks/README.md`](databricks/README.md) — fetch behavior, performance, SQL examples
- [`RUNBOOK.md`](RUNBOOK.md) — full AWS + Databricks runbook
