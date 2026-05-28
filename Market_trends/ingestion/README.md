# Experience Garage — Market Trends Ingestion

Bronze-layer ingestion for SAP Experience Garage market-trend signals. Writes gzip JSONL to S3; downstream Databricks Auto Loader and DLT own silver/gold.

## Architecture

```
External sources → This service → s3://eg-lakehouse/bronze/{category}/{source_id}/...
                              → s3://eg-lakehouse/bronze/_state/{source_id}.json
                              → s3://eg-lakehouse/bronze/_dlq/{source_id}/...
```

## Local setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- (Optional) Kaggle API credentials for `kaggle` source

### Install

```bash
cd ingestion
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run against real AWS S3 (`market-trend-exp2`)

Use a **named AWS profile** (avoid `RAG-Client` if that user is denied on the bucket):

```bash
# ~/.aws/credentials
# [eg-market-trends]
# aws_access_key_id = ...
# aws_secret_access_key = ...

# ingestion/.env
# EG_S3_BUCKET=market-trend-exp2
# AWS_PROFILE=eg-market-trends
# (do not set AWS_ENDPOINT_URL)

python scripts/aws_whoami.py   # confirm Arn before ingesting
python -m ingestion.main run --source techcrunch_ai
```

Bucket policy must allow the ARN printed by `aws_whoami.py`. See repo root `RUNBOOK.md`.

### Run with LocalStack S3

```bash
docker compose up -d localstack
docker compose up ingestion   # health server on :8080
```

Run a single source against LocalStack:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export EG_S3_BUCKET=eg-lakehouse

python -m ingestion.main run --source techcrunch_ai
python -m ingestion.main run --source pluralsight_blog
python -m ingestion.main run --source kaggle   # needs KAGGLE_USERNAME / KAGGLE_KEY
```

### Tests

```bash
pytest
ruff check src tests
mypy src
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `EG_ENV` | `dev` or `prod` (prod loads `EG_SECRETS_ID` from Secrets Manager) |
| `EG_S3_BUCKET` | Lakehouse bucket (default `eg-lakehouse`) |
| `EG_S3_BRONZE_PREFIX` | Bronze prefix (default `bronze`) |
| `AWS_PROFILE` | Named profile in `~/.aws/credentials` (recommended for non-default IAM user) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Optional explicit keys (override profile) |
| `AWS_ENDPOINT_URL` | LocalStack endpoint in dev |
| `EG_SECRETS_ID` | Secrets Manager secret JSON in prod |
| `KAGGLE_USERNAME` / `KAGGLE_KEY` | Kaggle API |
| `PRODUCT_HUNT_TOKEN` | Product Hunt GraphQL |
| `COURSERA_API_KEY` | Coursera Catalog API |
| `IDEANOTE_API_KEY` | Ideanote REST |
| `UDEMY_AFFILIATE_ID` | Udemy Affiliate API |

Never commit credentials. They are not stored in `sources.yaml`.

## Add a new RSS source

Edit `src/ingestion/config/sources.yaml`:

```yaml
  - id: my_new_feed
    category: news
    connector: rss_generic
    cadence_minutes: 30
    config:
      url: https://example.com/feed.xml
      keyword_filter: [AI, LLM]   # or null for no filter
```

No code change required. Deploy or run:

```bash
python -m ingestion.main run --source my_new_feed
```

## Add a custom connector

1. Subclass `BaseConnector` in `src/ingestion/connectors/{category}/my_source.py`.
2. Implement `fetch(self, since)` yielding dicts with `external_id`, `raw`, and optional `source_published_at`, `source_url`.
3. Register in `src/ingestion/connectors/registry.py` (`CONNECTOR_CLASSES`).
4. Add entry to `sources.yaml`.
5. Add `tests/test_my_source.py` with a VCR cassette or fixture.

## Implemented connectors (E2E tested)

| Source | Category | Connector |
|--------|----------|-----------|
| `kaggle` | builder | Official Kaggle SDK |
| `techcrunch_ai` | news | `rss_generic` |
| `pluralsight_blog` | learning | `rss_generic` |

All other sources in `sources.yaml` have stub classes raising `ConnectorError` until implemented.

## CLI

```bash
python -m ingestion.main run --source techcrunch_ai
python -m ingestion.main run --group rss_30      # all 30-min cadence sources
python -m ingestion.main run --all
python -m ingestion.main health                 # /healthz on :8080
```

## Bronze record shape

```json
{
  "source_id": "techcrunch_ai",
  "category": "news",
  "ingested_at": "2026-05-20T10:00:00Z",
  "source_published_at": "2026-05-19T14:32:00Z",
  "source_url": "https://...",
  "external_id": "<stable id>",
  "raw": { }
}
```

Files: `bronze/{category}/{source_id}/dt=YYYY-MM-DD/run_{timestamp}.jsonl.gz`

## Silver content fetch (Databricks — Option A)

Full article text is **not** fetched at bronze. Use the Databricks pipeline in `../databricks/`:

- Auto Loader reads `s3://eg-lakehouse/bronze/**/*.jsonl.gz`
- Fetches each `source_url`, writes `silver_market_content` with `body_text`
- Query `silver_market_content_for_llm` for LLM / mission ideation

See [databricks/README.md](../databricks/README.md).

## Deployment

1. Build and push images:
   - `Dockerfile` — RSS/API workers
   - `Dockerfile.playwright` — Playwright scrapers (6h cadence)
2. `terraform apply` in `infra/terraform/` — S3 bucket (versioning + 90d Glacier for `bronze/`), ECR, ECS Fargate task defs per cadence group, EventBridge schedules.
3. Store API keys in AWS Secrets Manager (`EG_SECRETS_ID`).
4. Wire Unity Catalog external location to `s3://eg-lakehouse/bronze/` (owned by Databricks team).

## Out of scope

Silver/gold DLT, schema normalization, FastAPI serving layer, and non–market-trend signals (interviews, recommendations, events).
