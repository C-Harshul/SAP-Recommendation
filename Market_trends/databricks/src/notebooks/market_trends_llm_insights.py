# Databricks notebook source
# MAGIC %md
# MAGIC # EG Market Trends — LLM insights (gold)
# MAGIC
# MAGIC Reads **`silver_market_content_for_llm`** (`body_text` + `source_url`), writes:
# MAGIC - `gold_market_trend_summaries` — per-article `ai_summarize`
# MAGIC - Optional mission brief via `ai_query` over recent summaries
# MAGIC
# MAGIC **Prerequisite:** Silver pipeline has populated `body_text` (URLs already fetched in silver step).

# COMMAND ----------

dbutils.widgets.text("catalog", "market-trends-exp")
dbutils.widgets.text("schema", "experience_garage_dev")
dbutils.widgets.text("summary_limit", "200")
dbutils.widgets.text("mission_source_limit", "30")
dbutils.widgets.dropdown("run_mission_brief", "true", ["true", "false"])

# COMMAND ----------

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
summary_limit = int(dbutils.widgets.get("summary_limit"))
mission_limit = int(dbutils.widgets.get("mission_source_limit"))
run_mission = dbutils.widgets.get("run_mission_brief").lower() == "true"

silver = f"`{catalog}`.{schema}.silver_market_content_for_llm"
gold = f"`{catalog}`.{schema}.gold_market_trend_summaries"
brief = f"`{catalog}`.{schema}.gold_mission_brief"

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {gold}
COMMENT 'LLM summaries of ingested articles'
AS
SELECT
  source_id,
  category,
  external_id,
  source_url,
  source_published_at,
  ingested_at,
  content_fetch_status,
  ai_summarize(
    concat(
      'Article URL: ', coalesce(source_url, 'unknown'), '\\n\\n',
      substring(body_text, 1, 12000)
    ),
    120
  ) AS article_summary,
  current_timestamp() AS summarized_at
FROM {silver}
WHERE body_text IS NOT NULL
  AND length(trim(body_text)) > 100
ORDER BY source_published_at DESC NULLS LAST
LIMIT {summary_limit}
""")

display(spark.sql(f"SELECT COUNT(*) AS summaries FROM {gold}"))

# COMMAND ----------

if run_mission:
    spark.sql(f"""
    CREATE OR REPLACE TABLE {brief}
    COMMENT 'Weekly mission brief synthesized from gold summaries'
    AS
    WITH recent AS (
      SELECT source_id, source_url, article_summary, source_published_at
      FROM {gold}
      ORDER BY source_published_at DESC NULLS LAST
      LIMIT {mission_limit}
    ),
    bundled AS (
      SELECT concat_ws(
        '\\n\\n---\\n\\n',
        collect_list(
          concat('[', source_id, '] ', source_url, '\\n', article_summary)
        )
      ) AS context
      FROM recent
    )
    SELECT
      ai_query(
        'databricks-meta-llama-3-3-70b-instruct',
        concat(
          'You are a strategist for SAP Experience Garage. ',
          'Using ONLY the sources below, produce:\\n',
          '1) Five market themes (bullets)\\n',
          '2) Three mission workshop ideas for SAP\\n',
          '3) For each theme, cite [source_id] and URL\\n\\n',
          'SOURCES:\\n',
          context
        )
      ) AS mission_brief,
      current_timestamp() AS generated_at
    FROM bundled
    """)
    display(spark.sql(f"SELECT * FROM {brief}"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Browse links + summaries
# MAGIC
# MAGIC ```sql
# MAGIC SELECT source_id, source_url, article_summary
# MAGIC FROM gold_market_trend_summaries
# MAGIC ORDER BY source_published_at DESC
# MAGIC LIMIT 20;
# MAGIC ```
