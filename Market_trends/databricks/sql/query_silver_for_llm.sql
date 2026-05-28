-- Curated silver rows for LLM / Experience Garage mission brainstorming.
-- Catalog: market-trends-exp (use backticks in SQL because of hyphens).

SELECT
  source_id,
  category,
  external_id,
  source_url,
  source_published_at,
  ingested_at,
  feed_summary,
  body_text,
  content_fetch_status,
  content_fetched_at
FROM `market-trends-exp`.experience_garage_dev.silver_market_content_for_llm
WHERE source_published_at >= current_timestamp() - INTERVAL 14 DAYS
ORDER BY source_published_at DESC NULLS LAST
LIMIT 100;
