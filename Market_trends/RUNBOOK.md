# Experience Garage market trends — AWS S3 + Databricks

**Goal:** Ingestion writes bronze to **AWS S3** → Databricks pipeline reads S3 → **silver tables** in catalog `market-trends-exp`.

## Architecture

```
Ingestion (local/ECS)  →  s3://market-trend-exp2/bronze/...
                              ↓  (UC external location)
Databricks pipeline  →  market-trends-exp.experience_garage_dev.bronze_market_trends
                              ↓
                         silver_market_content (+ body_text)
                              ↓
                         silver_market_content_for_llm  ← query / Gemini
```

## Step 0 — Choose an AWS client (not RAG-Client)

Ingestion uses the **standard AWS credential chain** (no hardcoded IAM user). Pick one identity and stick to it:

1. Create or pick an IAM **user** or **role** with `s3:ListBucket`, `s3:PutObject`, `s3:GetObject` on `market-trend-exp2` / `bronze/*`.
2. Add keys to `~/.aws/credentials` under a **named profile** (recommended):

   ```ini
   [eg-market-trends]
   aws_access_key_id = AKIA...
   aws_secret_access_key = ...
   ```

3. In `ingestion/.env`, set:

   ```bash
   AWS_PROFILE=eg-market-trends
   ```

   Do **not** leave `AWS_PROFILE` unset if your `[default]` profile is still `RAG-Client`.

4. Confirm which identity is active:

   ```bash
   cd ingestion && source .venv/bin/activate
   python scripts/aws_whoami.py
   ```

   Use the printed **ARN** in Step 1 (bucket policy), not `RAG-Client` unless you intentionally use that user.

## Step 1 — Fix AWS S3 access (required)

The bucket `market-trend-exp2` must allow **your ingestion principal** from Step 0. Remove any **explicit Deny** on that principal.

**Option A — Terraform** (admin AWS creds; install: `brew install hashicorp/tap/terraform`):

```bash
cd ingestion/infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit ARNs (or use committed terraform.tfvars)
terraform init
AWS_PROFILE=YOUR_ADMIN_PROFILE terraform apply -target=aws_s3_bucket_policy.market_trend_exp
```

**Option A2 — Python** (same admin creds, no Terraform):

```bash
cd ingestion
AWS_PROFILE=YOUR_ADMIN_PROFILE python scripts/apply_bucket_policy.py
```

**Option A3 — Console:** Paste `ingestion/infra/bucket-policy-market-trend-exp2.json` in S3 → `market-trend-exp2` → Permissions → Bucket policy (remove explicit Deny first).

**Option B — Console:** Bucket policy on `market-trend-exp2` — allow your ingestion user/role `s3:ListBucket`, `s3:GetObject`, `s3:PutObject` on `bronze/*`.

Verify (with the same profile as ingestion):

```bash
export AWS_PROFILE=eg-market-trends   # same as .env
aws s3 ls s3://market-trend-exp2/bronze/
```

## Step 2 — Databricks external location (required)

Databricks must read `s3://market-trend-exp2/bronze/`. A **metastore admin** does this once:

1. **Catalog Explorer → Credentials → Create storage credential** (AWS IAM role with access to `market-trend-exp2`).
2. Run `databricks/sql/setup_external_location.sql` (replace `YOUR_STORAGE_CREDENTIAL`).
3. Or CLI:

```bash
databricks external-locations create market_trend_exp2_bronze \
  "s3://market-trend-exp2/bronze/" YOUR_STORAGE_CREDENTIAL \
  --profile harshul@numina-ai.com
```

Re-apply bucket policy with Databricks role ARN:

```bash
terraform apply -target=aws_s3_bucket_policy.market_trend_exp \
  -var="databricks_uc_role_arn=arn:aws:iam::ACCOUNT:role/YOUR_UC_ROLE"
```

## Step 3 — Ingest to S3

```bash
cd ingestion
source .venv/bin/activate
# .env: EG_S3_BUCKET=market-trend-exp2, AWS_PROFILE=your-profile, no AWS_ENDPOINT_URL
python scripts/aws_whoami.py
python -m ingestion.main run --source techcrunch_ai
python -m ingestion.main run --all
```

## Step 4 — Deploy & run Databricks pipeline

```bash
cd databricks
databricks bundle deploy -t dev --profile harshul@numina-ai.com
databricks bundle run market_trends_content_pipeline -t dev --profile harshul@numina-ai.com
```

## Step 5 — View in Databricks

```sql
SELECT COUNT(*) FROM `market-trends-exp`.experience_garage_dev.bronze_market_trends;
SELECT source_id, source_url, LEFT(body_text, 300), content_fetch_status
FROM `market-trends-exp`.experience_garage_dev.silver_market_content_for_llm
LIMIT 20;
```

## Catalog / paths

| Item | Value |
|------|--------|
| S3 bucket | `market-trend-exp2` |
| Bronze prefix | `bronze/` |
| UC catalog | `market-trends-exp` |
| Dev schema | `experience_garage_dev` |

## Troubleshooting

| Error | Fix |
|-------|-----|
| `explicit deny` on S3 | Step 1 |
| Pipeline `403` on `s3://market-trend-exp2` | Step 2 external location |
| `Catalog main does not exist` | Use `market-trends-exp` (already configured) |
| Pipeline `%pip` error | Fixed — redeploy bundle |
