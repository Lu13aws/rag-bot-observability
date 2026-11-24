-- Fictional model prices (reference data, CSV with header row).
-- Used for KPI-06 cost per query. __BUCKET__ is replaced at runtime.
CREATE EXTERNAL TABLE IF NOT EXISTS model_pricing (
  model_id         string,
  price_in_per_1k  decimal(10,6),  -- USD per 1,000 input tokens
  price_out_per_1k decimal(10,6),  -- USD per 1,000 output tokens
  valid_from       date
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://__BUCKET__/reference/model_pricing/'
TBLPROPERTIES ('skip.header.line.count' = '1')
