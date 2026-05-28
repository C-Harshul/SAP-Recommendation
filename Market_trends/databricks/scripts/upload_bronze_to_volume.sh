#!/usr/bin/env bash
# Copy LocalStack bronze JSONL into UC Volume (workaround when market-trend-exp2 S3 is denied).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INGESTION="$ROOT/ingestion"
EXPORT="/tmp/eg-bronze-export"
VOLUME="dbfs:/Volumes/market-trends-exp/experience_garage_dev/bronze"
PROFILE="${DATABRICKS_PROFILE:-harshul@numina-ai.com}"

echo "Syncing LocalStack bronze → $EXPORT ..."
mkdir -p "$EXPORT"
cd "$INGESTION"
docker compose exec -T localstack awslocal s3 sync s3://eg-lakehouse/bronze /tmp/bronze-export \
  --exclude "_state/*" --exclude "_dlq/*"
docker cp ingestion-localstack-1:/tmp/bronze-export/. "$EXPORT/"

echo "Uploading to $VOLUME ..."
databricks fs cp -r --overwrite "$EXPORT" "$VOLUME" --profile "$PROFILE"

echo "Done. Run: databricks bundle run market_trends_content_pipeline -t dev"
