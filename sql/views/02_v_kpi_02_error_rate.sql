-- KPI-02 Error rate: count(status in ('error', 'timeout')) / count(all queries).
-- Per period and dimension combination (user_group, model_id, app_version).
-- Target: < 2 %, evaluated per day; not evaluated below 200 queries or for
-- incomplete periods.
CREATE OR REPLACE VIEW v_kpi_02_error_rate AS
WITH agg AS (
  SELECT
    grain, period_label, period_start, period_end, is_complete_period,
    dim_user_group, dim_model_id, dim_app_version,
    count_if(status IN ('error', 'timeout')) AS failed,
    count(*)                                 AS total
  FROM v_query_period
  GROUP BY grain, period_label, period_start, period_end, is_complete_period,
           dim_user_group, dim_model_id, dim_app_version
)
SELECT
  'KPI-02'                                  AS kpi_id,
  grain, period_label, period_start, period_end, is_complete_period,
  dim_user_group                            AS user_group,
  dim_model_id                              AS model_id,
  dim_app_version                           AS app_version,
  CAST(failed AS double)                    AS numerator,
  CAST(total AS double)                     AS denominator,
  CAST(failed AS double) / nullif(total, 0) AS kpi_value,
  total                                     AS sample_size,
  CAST(200 AS bigint)                       AS min_sample,
  'day'                                     AS target_grain,
  '<'                                       AS target_operator,
  0.02e0                                    AS target_value,
  (grain = 'day' AND is_complete_period AND total >= 200) AS is_evaluated,
  (grain = 'day' AND is_complete_period AND total >= 200
     AND CAST(failed AS double) / total >= 0.02)          AS target_breached
FROM agg
