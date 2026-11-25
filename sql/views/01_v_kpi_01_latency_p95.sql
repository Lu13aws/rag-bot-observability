-- KPI-01 Response time (p95): p95 of latency_ms over successful queries.
-- Exact nearest rank: the value at rank ceil(0.95 * n) in ascending order.
-- ceil(0.95 * n) is computed with integers: (95 * n + 99) / 100.
-- Calculated per period and dimension combination (user_group, model_id,
-- app_version, each incl. 'all'), because percentiles cannot be re-aggregated.
-- Target: < 8,000 ms, evaluated per day; not evaluated below 100 successful
-- queries (assumption, see KPI catalog) or for incomplete periods.
CREATE OR REPLACE VIEW v_kpi_01_latency_p95 AS
WITH ranked AS (
  SELECT
    grain, period_label, period_start, period_end, is_complete_period,
    dim_user_group, dim_model_id, dim_app_version, latency_ms,
    row_number() OVER (PARTITION BY grain, period_label, dim_user_group, dim_model_id, dim_app_version
                       ORDER BY latency_ms) AS rn,
    count(*)     OVER (PARTITION BY grain, period_label, dim_user_group, dim_model_id, dim_app_version) AS n
  FROM v_query_period
  WHERE status = 'success'
),
agg AS (
  SELECT
    grain, period_label, period_start, period_end, is_complete_period,
    dim_user_group, dim_model_id, dim_app_version,
    max(n)                                                      AS sample_size,
    max(CASE WHEN rn = (95 * n + 99) / 100 THEN latency_ms END) AS p95_latency_ms
  FROM ranked
  GROUP BY grain, period_label, period_start, period_end, is_complete_period,
           dim_user_group, dim_model_id, dim_app_version
)
SELECT
  'KPI-01'                          AS kpi_id,
  grain, period_label, period_start, period_end, is_complete_period,
  dim_user_group                    AS user_group,
  dim_model_id                      AS model_id,
  dim_app_version                   AS app_version,
  CAST(NULL AS double)              AS numerator,
  CAST(NULL AS double)              AS denominator,
  CAST(p95_latency_ms AS double)    AS kpi_value,
  sample_size,
  CAST(100 AS bigint)               AS min_sample,
  'day'                             AS target_grain,
  '<'                               AS target_operator,
  8000e0                            AS target_value,
  (grain = 'day' AND is_complete_period AND sample_size >= 100) AS is_evaluated,
  (grain = 'day' AND is_complete_period AND sample_size >= 100
     AND p95_latency_ms >= 8000)                                AS target_breached
FROM agg
