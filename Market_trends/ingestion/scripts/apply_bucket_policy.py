#!/usr/bin/env python3
"""Apply market-trend-exp2 bucket policy (no Terraform required).

Requires AWS credentials that can s3:PutBucketPolicy (account/bucket admin).
Bronze-writer user cannot run this — use an admin profile:

  AWS_PROFILE=your-admin-profile python scripts/apply_bucket_policy.py

Optional: --databricks-role-arn for UC pipeline reads.
"""

from __future__ import annotations

import argparse
import json
import sys

import boto3
from botocore.exceptions import ClientError

BUCKET = "market-trend-exp2"
INGESTION_USER_ARN = (
    "arn:aws:iam::318651457457:user/market-trend-exp-bronze-writer"
)


def build_policy(ingestion_arn: str, databricks_role_arn: str | None) -> dict:
    statements: list[dict] = [
        {
            "Sid": "AllowIngestionUser",
            "Effect": "Allow",
            "Principal": {"AWS": ingestion_arn},
            "Action": ["s3:ListBucket"],
            "Resource": f"arn:aws:s3:::{BUCKET}",
        },
        {
            "Sid": "AllowIngestionUserObjects",
            "Effect": "Allow",
            "Principal": {"AWS": ingestion_arn},
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
            "Resource": f"arn:aws:s3:::{BUCKET}/bronze/*",
        },
    ]
    if databricks_role_arn:
        statements.extend(
            [
                {
                    "Sid": "AllowDatabricksUC",
                    "Effect": "Allow",
                    "Principal": {"AWS": databricks_role_arn},
                    "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
                    "Resource": f"arn:aws:s3:::{BUCKET}",
                },
                {
                    "Sid": "AllowDatabricksUCObjects",
                    "Effect": "Allow",
                    "Principal": {"AWS": databricks_role_arn},
                    "Action": ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"],
                    "Resource": f"arn:aws:s3:::{BUCKET}/bronze/*",
                },
            ]
        )
    return {"Version": "2012-10-17", "Statement": statements}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ingestion-arn",
        default=INGESTION_USER_ARN,
        help="IAM user/role ARN for bronze ingestion",
    )
    parser.add_argument(
        "--databricks-role-arn",
        default=None,
        help="Databricks UC IAM role ARN (optional)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print policy only")
    args = parser.parse_args()

    policy = build_policy(args.ingestion_arn, args.databricks_role_arn)
    print(json.dumps(policy, indent=2))

    if args.dry_run:
        return 0

    s3 = boto3.client("s3")
    try:
        s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps(policy))
    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"\nFailed ({code}): {e.response['Error']['Message']}", file=sys.stderr)
        print(
            "\nUse an AWS admin profile (not market-trend-exp-bronze-writer), or paste "
            "the JSON above in S3 Console → market-trend-exp2 → Permissions → Bucket policy.",
            file=sys.stderr,
        )
        return 1

    print(f"\nApplied bucket policy on s3://{BUCKET}/")
    print("Verify with bronze-writer profile:")
    print("  AWS_PROFILE=market-trend-exp-bronze-writer python -c \"import boto3; ...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
