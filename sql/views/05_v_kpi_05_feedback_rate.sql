-- KPI-05 Feedback rate: count(feedback is not null) / count(all queries).
-- Per period and dimension combination.
-- Target: >= 5 %, evaluated per ISO week (complete periods only).
CREATE OR REPLACE VIEW v_kpi_05_feedback_rate AS
WITH agg AS (
  SELECT
    grain, period_label, period_start, period_end, is_complete_period,
    dim_user_group, dim_model_id, dim_app_version,
    count_if(feedback IS NOT NULL) AS rated,
    count(*)                       AS total
  FROM v_query_period
  GROUP BY grain, period_label, period_start, period_end, is_complete_period,
           dim_user_group, dim_model_id, dim_app_version
)
SELECT
  'KPI-05'                                 AS kpi_id,
  grain, period_label, period_start, period_end, is_complete_period,
  dim_user_group                           AS user_group,
  dim_model_id                             AS model_id,
  dim_app_version                          AS app_version,
  CAST(rated AS double)                    AS numerator,
  CAST(total AS double)                    AS denominator,
  CAST(rated AS double) / nullif(total, 0) AS kpi_value,
  total                                    AS sample_size,
  CAST(NULL AS bigint)                     AS min_sample,
  'week'                                   AS target_grain,
  '>='                                     AS target_operator,
  0.05e0                                   AS target_value,
  (grain = 'week' AND is_complete_period)                                          AS is_evaluated,
  (grain = 'week' AND is_complete_period AND CAST(rated AS double) / total < 0.05) AS target_breached
FROM agg
