-- Unity Catalog: wire Databricks to AWS S3 bronze (market-trend-exp2).
-- Run as METASTORE ADMIN in Databricks SQL.
--
-- Prerequisite: Storage credential with IAM role that can read s3://market-trend-exp2/bronze/
-- See RUNBOOK.md Step 2 and https://docs.databricks.com/en/connect/unity-catalog/cloud-storage/

CREATE EXTERNAL LOCATION IF NOT EXISTS market_trend_exp2_bronze
URL 's3://market-trend-exp2/bronze/'
WITH (STORAGE CREDENTIAL `YOUR_STORAGE_CREDENTIAL`)
COMMENT 'EG market trends bronze JSONL on AWS S3 (market-trend-exp2)';

GRANT READ FILES ON EXTERNAL LOCATION market_trend_exp2_bronze TO `harshul@numina-ai.com`;
GRANT WRITE FILES ON EXTERNAL LOCATION market_trend_exp2_bronze TO `harshul@numina-ai.com`;

-- Verify (after ingestion wrote files):
-- LIST 's3://market-trend-exp2/bronze/news/';

-- Then deploy & run pipeline:
--   databricks bundle run market_trends_content_pipeline -t dev
