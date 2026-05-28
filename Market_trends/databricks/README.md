# Databricks — Silver content enrichment (Option A)

Reads **bronze** JSONL from S3 (written by `ingestion/`), fetches each article URL, extracts text with **trafilatura**, and writes **silver** Delta tables for LLM / Experience Garage mission ideation.

```
ingestion (ECS) → s3://eg-lakehouse/bronze/...
                        ↓ Auto Loader (DLT)
                  bronze_market_trends
                        ↓ dedupe + HTTP fetch
                  silver_market_content
                        ↓ curated view
                  silver_market_content_for_llm
```

## Full setup checklist

See **[SETUP.md](SETUP.md)** — S3 bucket IAM + UC external location are required before the pipeline can read bronze.

## Prerequisites

1. **Catalog `market-trends-exp`** — must exist before `bundle deploy`. Create once:
   - **UI:** Catalog Explorer → **Create catalog** → name `market-trends-exp` → enable **Default Storage** (recommended), or
   - **SQL:** run `sql/create_catalog.sql` in Databricks SQL.
2. **Real S3** — bronze on AWS (not LocalStack). Default path: `s3://market-trend-exp2/bronze/` (override with `--var bronze_s3_path=...`).
3. **Unity Catalog** — external location + storage credential for your bronze S3 prefix.
4. **Databricks CLI** authenticated to your workspace:
   ```bash
   databricks auth login --host https://dbc-de47fb26-18b8.cloud.databricks.com
   ```
5. Adjust `databricks.yml` if your bucket or catalog name differs.

## Deploy and run

```bash
cd databricks
databricks bundle deploy -t dev
databricks bundle run market_trends_content_pipeline -t dev
```

Or run the pipeline from **Workflows → Lakeflow PLT / DLT** in the UI.

Pipeline notebook: `src/notebooks/market_trends_content_pipeline.py`

## Tables (Unity Catalog)

| Table | Description |
|-------|-------------|
| `{catalog}.{schema}.bronze_market_trends` | Streaming load of bronze JSONL from S3 |
| `{catalog}.{schema}.bronze_market_trends_latest` | View: latest row per `external_id` |
| `{catalog}.{schema}.silver_market_content` | + `body_text`, `content_fetch_status`, `feed_summary` |
| `{catalog}.{schema}.silver_market_content_for_llm` | Rows with non-empty `body_text` for prompts |

Default dev target: `market-trends-exp.experience_garage_dev.*`

## Query for Gemini / mission ideas

See **`sql/create_gold_llm_insights.sql`** and **`sql/mission_brief_ai_query.sql`**.

Run LLM gold job (after silver is populated):

```bash
databricks bundle run market_trends_llm_insights -t dev
```

Or notebook: `src/notebooks/market_trends_llm_insights.py`

```sql
SELECT source_id, source_url, article_summary
FROM `market-trends-exp`.experience_garage_dev.gold_market_trend_summaries
ORDER BY source_published_at DESC LIMIT 20;

SELECT mission_brief FROM `market-trends-exp`.experience_garage_dev.gold_mission_brief;
```

Silver source text (before LLM):

```sql
SELECT
  source_id,
  category,
  source_url,
  source_published_at,
  feed_summary,
  body_text,
  content_fetch_status
FROM `market-trends-exp`.experience_garage_dev.silver_market_content_for_llm
ORDER BY source_published_at DESC NULLS LAST
LIMIT 50;
```

Export to a notebook or `%python` and pass `body_text` + `source_url` to your LLM — not bare URLs.

## Fetch behavior

- HTTP GET + **trafilatura** extract; 2s delay per host per executor process
- On failure: falls back to RSS `feed_summary` / `title` from `raw`
- `content_fetch_status`: `ok`, `http_error`, `empty_extract`, `error`, `no_url`, `skipped`
- Paywalled sites may stay `empty_extract` / `http_error` — expect feed fallback

## Performance notes

- First full refresh fetches **every** distinct URL in bronze — can take hours at scale.
- Schedule pipeline after ingestion cadence (e.g. hourly).
- Future: incremental fetch only for new `external_id` (merge / `apply_changes`).

## Local test of fetch logic

```bash
cd databricks
python -c "
from src.content_fetch import fetch_article_content
r = fetch_article_content('https://openai.com/blog', 'fallback')
print(r['content_fetch_status'], (r['body_text'] or '')[:200])
"
```

## Related

- Bronze ingestion: `../ingestion/README.md`
- Do **not** point this pipeline at LocalStack; use production/staging S3 only.
