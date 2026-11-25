-- KPI-03 No-source share: successful queries with sources_count = 0
-- / successful queries. Per period and dimension combination.
-- Target: < 10 %, evaluated per ISO week.
CREATE OR REPLACE VIEW v_kpi_03_no_source_share AS
WITH agg AS (
  SELECT
    grain, period_label, period_start, period_end, is_complete_period,
    dim_user_group, dim_model_id, dim_app_version,
    count_if(status = 'success' AND sources_count = 0) AS no_source,
    count_if(status = 'success')                       AS successful
  FROM v_query_period
  GROUP BY grain, period_label, period_start, period_end, is_complete_period,
           dim_user_group, dim_model_id, dim_app_version
)
SELECT
  'KPI-03'                                          AS kpi_id,
  grain, period_label, period_start, period_end, is_complete_period,
  dim_user_group                                    AS user_group,
  dim_model_id                                      AS model_id,
  dim_app_version                                   AS app_version,
  CAST(no_source AS double)                         AS numerator,
  CAST(successful AS double)                        AS denominator,
  CAST(no_source AS double) / nullif(successful, 0) AS kpi_value,
  successful                                        AS sample_size,
  CAST(NULL AS bigint)                              AS min_sample,
  'week'                                            AS target_grain,
  '<'                                               AS target_operator,
  0.10e0                                            AS target_value,
  (grain = 'week' AND is_complete_period AND successful > 0) AS is_evaluated,
  (grain = 'week' AND is_complete_period AND successful > 0
     AND CAST(no_source AS double) / successful >= 0.10)     AS target_breached
FROM agg
