# Setup checklist — market-trends-exp end-to-end

## Done automatically

- [x] Unity Catalog **`market-trends-exp`** created
- [x] Schema **`experience_garage_dev`** created
- [x] Bundle deployed (`databricks bundle deploy -t dev`)
- [x] Pipeline notebook fixed (`%pip` at top)
- [x] Ingestion `.env` → `EG_S3_BUCKET=market-trend-exp2` (real AWS, no LocalStack)

## Required before pipeline + ingestion work (platform / AWS admin)

### 1. S3 bucket policy — allow your ingestion IAM principal

Use any IAM user/role for ingestion — **not** tied to `RAG-Client`. Configure via `AWS_PROFILE` in `ingestion/.env` (see `RUNBOOK.md` Step 0).

**Action:** Update the `market-trend-exp2` bucket policy to allow `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` for:

- Your **ingestion** IAM user/role ARN (`python ingestion/scripts/aws_whoami.py`), and
- Databricks UC storage credential IAM role (see step 2).

Remove any **explicit Deny** that blocks these principals.

### 2. Unity Catalog external location (Databricks → S3)

Pipeline failed with **403 Forbidden** / `AnonymousAWSCredentials` on `s3://market-trend-exp2/bronze/`.

**Action:** In Databricks (or SQL), create:

1. **Storage credential** pointing at IAM role that can read/write `s3://market-trend-exp2/`
2. **External location** e.g. `market_trend_exp2_bronze` → `s3://market-trend-exp2/bronze/`
3. **GRANT** `READ FILES` / `WRITE FILES` on that location to users/groups running the pipeline

Example SQL (adjust credential name after creating in UI):

```sql
-- Run in Databricks SQL after creating storage credential in Catalog Explorer
CREATE EXTERNAL LOCATION IF NOT EXISTS market_trend_exp2_bronze
URL 's3://market-trend-exp2/bronze/'
WITH (STORAGE CREDENTIAL `your_storage_credential_name`);

GRANT READ FILES ON EXTERNAL LOCATION market_trend_exp2_bronze TO `harshul@numina-ai.com`;
GRANT WRITE FILES ON EXTERNAL LOCATION market_trend_exp2_bronze TO `harshul@numina-ai.com`;
```

See `sql/setup_external_location.sql`.

### 3. Run ingestion (after S3 access works)

```bash
cd ingestion
source .venv/bin/activate
python -m ingestion.main run --source techcrunch_ai
python -m ingestion.main run --all   # optional full pull
```

Verify:

```bash
aws s3 ls s3://market-trend-exp2/bronze/ --recursive | head
```

### 4. Run silver pipeline

```bash
cd databricks
databricks bundle run market_trends_content_pipeline -t dev --profile harshul@numina-ai.com
```

### 5. Query results

```sql
SELECT source_id, source_url, LEFT(body_text, 200), content_fetch_status
FROM `market-trends-exp`.experience_garage_dev.silver_market_content_for_llm
LIMIT 20;
```

## LocalStack data (optional migration)

Bronze from LocalStack is under `eg-lakehouse` locally. To copy to real S3 once access works:

```bash
aws s3 sync s3://eg-lakehouse/bronze/ s3://market-trend-exp2/bronze/ \
  --endpoint-url http://localhost:4566 \
  --source-region us-east-1
```

(Only if LocalStack still has the data.)

## Quick reference

| Component | Value |
|-----------|--------|
| Catalog | `market-trends-exp` |
| Dev schema | `experience_garage_dev` |
| S3 bronze | `s3://market-trend-exp2/bronze/` |
| Pipeline | `[dev] EG market trends — bronze → silver content` |
