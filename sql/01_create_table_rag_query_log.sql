-- Query logs written by the Glue job (Parquet/Snappy, one partition per dt).
-- Columns and types: docs/01-requirements.md, section 5.1.
-- Partition projection: Athena derives the dt partitions from the range below,
-- so no MSCK REPAIR TABLE or crawler is needed.
-- __BUCKET__ is replaced at runtime by infra/07_athena.sh.
CREATE EXTERNAL TABLE IF NOT EXISTS rag_query_log (
  query_id      string,
  event_ts      timestamp,   -- UTC
  status        string,      -- success | error | timeout
  error_type    string,
  latency_ms    int,
  sources_count int,
  tokens_in     int,
  tokens_out    int,
  feedback      smallint,    -- 1 | -1 | null
  model_id      string,
  app_version   string,
  user_group    string
)
PARTITIONED BY (dt string)  -- local date Europe/Zurich, YYYY-MM-DD
STORED AS PARQUET
LOCATION 's3://__BUCKET__/processed/rag_query_log/'
TBLPROPERTIES (
  'parquet.compression'        = 'SNAPPY',
  'projection.enabled'         = 'true',
  'projection.dt.type'         = 'date',
  'projection.dt.format'       = 'yyyy-MM-dd',
  'projection.dt.range'        = '2026-08-01,2026-10-29',
  'projection.dt.interval'     = '1',
  'projection.dt.interval.unit'= 'DAYS',
  'storage.location.template'  = 's3://__BUCKET__/processed/rag_query_log/dt=${dt}/'
)
