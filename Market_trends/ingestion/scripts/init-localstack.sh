#!/bin/bash
set -euo pipefail
awslocal s3 mb s3://eg-lakehouse 2>/dev/null || true
awslocal s3api put-bucket-versioning \
  --bucket eg-lakehouse \
  --versioning-configuration Status=Enabled
echo "LocalStack S3 bucket eg-lakehouse ready"
