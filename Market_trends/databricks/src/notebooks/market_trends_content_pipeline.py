# Databricks notebook source
# MAGIC %pip install trafilatura httpx -q

# COMMAND ----------

# MAGIC %md
# MAGIC # EG Market Trends — Silver content enrichment (Option A)
# MAGIC
# MAGIC Reads bronze JSONL from S3 (written by the ingestion service), fetches each
# MAGIC `source_url`, extracts article text, and writes **silver** Delta tables for LLM /
# MAGIC mission ideation downstream.
# MAGIC
# MAGIC **Prerequisites**
# MAGIC - Unity Catalog external location for `s3://market-trend-exp2/bronze/`
# MAGIC - Catalog `market-trends-exp`, schema `experience_garage_dev`
# MAGIC - Ingestion service has populated bronze on real S3 (not LocalStack)

# COMMAND ----------

import dlt
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

# Inline fetch module so the pipeline works when only this notebook is deployed.
# (Canonical copy: ../content_fetch.py — keep in sync for local tests.)
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

_FETCH_BY_HOST: dict[str, float] = {}
_MAX_BODY_CHARS = 80_000
_USER_AGENT = (
    "ExperienceGarage-MarketTrends/1.0 (+https://sap.com; research ingestion; "
    "contact: experience-garage-internal)"
)


def _rate_limit(url: str, delay_seconds: float) -> None:
    try:
        host = urlparse(url).netloc or "unknown"
    except Exception:
        host = "unknown"
    now = time.monotonic()
    last = _FETCH_BY_HOST.get(host, 0.0)
    wait = delay_seconds - (now - last)
    if wait > 0:
        time.sleep(wait)
    _FETCH_BY_HOST[host] = time.monotonic()


def fetch_article_content(
    url: str | None,
    feed_summary: str | None = None,
    delay_seconds: float = 2.0,
) -> dict[str, Any]:
    fetched_at = datetime.now(UTC).isoformat()
    if not url or not str(url).strip():
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "no_url",
            "content_fetch_error": None,
            "content_fetched_at": fetched_at,
        }
    url = str(url).strip()
    try:
        import trafilatura
    except ImportError:
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "skipped",
            "content_fetch_error": "trafilatura not installed",
            "content_fetched_at": fetched_at,
        }
    _rate_limit(url, delay_seconds)
    try:
        with httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                return {
                    "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
                    "content_fetch_status": "http_error",
                    "content_fetch_error": f"HTTP {resp.status_code}",
                    "content_fetched_at": fetched_at,
                }
            html = resp.text
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
        if text and text.strip():
            return {
                "body_text": text.strip()[:_MAX_BODY_CHARS],
                "content_fetch_status": "ok",
                "content_fetch_error": None,
                "content_fetched_at": fetched_at,
            }
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "empty_extract",
            "content_fetch_error": "trafilatura returned no text",
            "content_fetched_at": fetched_at,
        }
    except Exception as exc:
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "error",
            "content_fetch_error": str(exc)[:500],
            "content_fetched_at": fetched_at,
        }


spark: SparkSession = spark  # type: ignore[name-defined]

BRONZE_BASE = spark.conf.get("bronze_s3_path", "s3://market-trend-exp2/bronze").rstrip("/")
FETCH_DELAY = float(spark.conf.get("content_fetch_delay_seconds", "2"))


def _bronze_glob_path() -> str:
    """Glob bronze JSONL under S3 or Volume: {base}/{category}/{source}/dt=.../*.jsonl.gz"""
    if BRONZE_BASE.startswith("s3://"):
        return f"{BRONZE_BASE}/*/*/*/*.jsonl.gz"
    return f"{BRONZE_BASE}/*/*/*/*.jsonl.gz"


def _feed_summary_col(df: DataFrame) -> DataFrame:
    """Pull title/summary from nested raw struct (schema varies by source)."""
    if "raw" not in df.columns:
        return df.withColumn("feed_summary", F.lit(None).cast("string"))
    raw_json = F.to_json(F.col("raw"))
    summary = F.coalesce(
        F.get_json_object(raw_json, "$.summary"),
        F.get_json_object(raw_json, "$.description"),
        F.get_json_object(raw_json, "$.title"),
        F.get_json_object(raw_json, "$.content"),
        F.get_json_object(raw_json, "$.text"),
    )
    return df.withColumn("feed_summary", summary)


@dlt.table(
    name="bronze_market_trends",
    comment="Bronze envelopes from ingestion (gzip JSONL on S3 or UC Volume)",
    table_properties={"quality": "bronze"},
)
def bronze_market_trends() -> DataFrame:
    path = _bronze_glob_path()
    df = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("compression", "gzip")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("rescuedDataColumn", "_rescued_data")
        .load(path)
        .withColumn("_source_file", F.col("_metadata.file_path"))
        .filter(
            ~F.col("_source_file").contains("/_state/")
            & ~F.col("_source_file").contains("/_dlq/")
        )
        .withColumn("_bronze_loaded_at", F.current_timestamp())
    )
    return df


@dlt.view(name="bronze_market_trends_latest")
def bronze_market_trends_latest() -> DataFrame:
    """One row per external_id (latest ingested_at)."""
    bronze = dlt.read("bronze_market_trends")
    w = Window.partitionBy("external_id").orderBy(F.desc("ingested_at"))
    return (
        bronze.withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )


_fetch_schema = T.StructType(
    [
        T.StructField("body_text", T.StringType(), True),
        T.StructField("content_fetch_status", T.StringType(), True),
        T.StructField("content_fetch_error", T.StringType(), True),
        T.StructField("content_fetched_at", T.StringType(), True),
    ]
)


@F.udf(_fetch_schema)
def _fetch_content_udf(url: str | None, feed_summary: str | None) -> dict:
    return fetch_article_content(url, feed_summary, delay_seconds=FETCH_DELAY)


@dlt.table(
    name="silver_market_content",
    comment="Bronze records plus fetched article body text for LLM / mission ideation",
    table_properties={"quality": "silver"},
)
def silver_market_content() -> DataFrame:
    base = dlt.read("bronze_market_trends_latest")
    base = _feed_summary_col(base)
    enriched = _fetch_content_udf(F.col("source_url"), F.col("feed_summary"))
    return (
        base.withColumn("_enriched", enriched)
        .withColumn("body_text", F.col("_enriched.body_text"))
        .withColumn("content_fetch_status", F.col("_enriched.content_fetch_status"))
        .withColumn("content_fetch_error", F.col("_enriched.content_fetch_error"))
        .withColumn("content_fetched_at", F.col("_enriched.content_fetched_at"))
        .drop("_enriched")
        .withColumn("_silver_processed_at", F.current_timestamp())
    )


@dlt.table(
    name="silver_market_content_for_llm",
    comment="Curated slice for LLM prompts: text + metadata, successful or feed fallback",
    table_properties={"quality": "silver"},
)
def silver_market_content_for_llm() -> DataFrame:
    s = dlt.read("silver_market_content")
    return s.select(
        "source_id",
        "category",
        "external_id",
        "source_url",
        "source_published_at",
        "ingested_at",
        "feed_summary",
        "body_text",
        "content_fetch_status",
        "content_fetched_at",
    ).filter(
        F.col("body_text").isNotNull() & (F.length(F.trim(F.col("body_text"))) > 0)
    )
