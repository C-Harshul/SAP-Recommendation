#!/usr/bin/env python3
"""Print the AWS identity boto3 will use (respects AWS_PROFILE and .env)."""

from __future__ import annotations

import os
import sys

# Load ingestion/.env when run from repo
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_env = os.path.join(_root, ".env")
if os.path.isfile(_env):
    for line in open(_env, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import boto3  # noqa: E402
from botocore.exceptions import ProfileNotFound

profile = os.environ.get("AWS_PROFILE", "(default profile)")
try:
    sts = boto3.client("sts")
    ident = sts.get_caller_identity()
except ProfileNotFound:
    print(f"AWS_PROFILE={profile}")
    print(f"\nProfile '{profile}' is set in .env but missing from ~/.aws/credentials.")
    print("Add a block like:\n")
    print(f"  [{profile}]")
    print("  aws_access_key_id = AKIA...")
    print("  aws_secret_access_key = ...")
    sys.exit(1)
print(f"AWS_PROFILE={profile}")
print(f"Account={ident['Account']}")
print(f"Arn={ident['Arn']}")
if "RAG-Client" in ident["Arn"]:
    print(
        "\nNote: You are still using RAG-Client. Set AWS_PROFILE in ingestion/.env "
        "to a different profile, or update ~/.aws/credentials [default].",
        file=sys.stderr,
    )
