-- Gold: per-article LLM summaries from silver body_text (Databricks ai_summarize).
-- Run in SQL Editor after silver_market_content_for_llm is populated.
-- Adjust LIMIT for cost/latency (each row = one model call).

CREATE OR REPLACE TABLE `market-trends-exp`.experience_garage_dev.gold_market_trend_summaries
COMMENT 'LLM summaries of ingested articles for Experience Garage mission ideation'
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
      'Article URL: ', coalesce(source_url, 'unknown'), '\n\n',
      substring(body_text, 1, 12000)
    ),
    120
  ) AS article_summary,
  current_timestamp() AS summarized_at
FROM `market-trends-exp`.experience_garage_dev.silver_market_content_for_llm
WHERE body_text IS NOT NULL
  AND length(trim(body_text)) > 100
ORDER BY source_published_at DESC NULLS LAST
LIMIT 200;
