-- Weekly mission brief: synthesize recent summaries into themes for Experience Garage.
-- Requires gold_market_trend_summaries (run create_gold_llm_insights.sql first).

WITH recent AS (
  SELECT
    source_id,
    source_url,
    article_summary
  FROM `market-trends-exp`.experience_garage_dev.gold_market_trend_summaries
  WHERE source_published_at >= current_timestamp() - INTERVAL 14 DAYS
  ORDER BY source_published_at DESC NULLS LAST
  LIMIT 30
),
bundled AS (
  SELECT concat_ws(
    '\n\n---\n\n',
    collect_list(
      concat('[', source_id, '] ', source_url, '\n', article_summary)
    )
  ) AS context
  FROM recent
)
SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  concat(
    'You are a strategist for SAP Experience Garage. ',
    'Using ONLY the sources below, produce:\n',
    '1) Five market themes (bullets)\n',
    '2) Three mission workshop ideas for SAP\n',
    '3) For each theme, cite [source_id] and URL\n\n',
    'SOURCES:\n',
    context
  )
) AS mission_brief
FROM bundled;
