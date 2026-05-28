#!/usr/bin/env bash
# Sync AWS S3 bronze (market-trend-exp2) → UC Volume for Databricks pipeline
# when UC external location on S3 is not configured yet.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INGESTION="$ROOT/ingestion"
EXPORT="${TMPDIR:-/tmp}/eg-bronze-s3-export"
BUCKET="${EG_S3_BUCKET:-market-trend-exp2}"
VOLUME="${DATABRICKS_BRONZE_VOLUME:-dbfs:/Volumes/market-trends-exp/experience_garage_dev/bronze}"
PROFILE="${AWS_PROFILE:-market-trend-exp-bronze-writer}"
DB_PROFILE="${DATABRICKS_PROFILE:-harshul@numina-ai.com}"

echo "Export s3://${BUCKET}/bronze → $EXPORT ..."
rm -rf "$EXPORT"
mkdir -p "$EXPORT"

cd "$INGESTION"
source .venv/bin/activate
export AWS_PROFILE="$PROFILE"
export EG_S3_BUCKET="$BUCKET"
export EXPORT="$EXPORT"
python - <<'PY'
import os, boto3, pathlib
bucket = os.environ["EG_S3_BUCKET"]
export = pathlib.Path(os.environ["EXPORT"])
s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=bucket, Prefix="bronze/"):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        if key.endswith("/") or "/_state/" in key or "/_dlq/" in key:
            continue
        dest = export / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, key, str(dest))
        print(" ", key)
print("Done.")
PY

echo "Uploading to $VOLUME ..."
databricks fs cp -r --overwrite "$EXPORT/bronze" "$VOLUME" --profile "$DB_PROFILE"

echo "Run pipeline with volume bronze path:"
echo "  cd databricks && databricks bundle run market_trends_content_pipeline -t dev \\"
echo "    --var bronze_s3_path=dbfs:/Volumes/market-trends-exp/experience_garage_dev/bronze"
