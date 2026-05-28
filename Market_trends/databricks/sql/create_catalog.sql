-- One-time: create Unity Catalog `market-trends-exp`
-- Run in Databricks SQL or a notebook (requires CREATE_CATALOG privilege).
--
-- If your account uses Default Storage, this is usually enough:
CREATE CATALOG IF NOT EXISTS `market-trends-exp`
COMMENT 'Experience Garage — market trends (bronze/silver/gold)';

-- Optional: default schema for dev tables
CREATE SCHEMA IF NOT EXISTS `market-trends-exp`.experience_garage_dev
COMMENT 'Dev tables for market trends pipeline';

CREATE SCHEMA IF NOT EXISTS `market-trends-exp`.experience_garage
COMMENT 'Prod tables for market trends pipeline';
