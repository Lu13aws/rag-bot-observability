-- KPI-04 Positive feedback: count(feedback = 1) / count(feedback is not null).
-- Per period and dimension combination.
-- Target: >= 75 %, evaluated per ISO week; not evaluated below 30 rated
-- queries or for incomplete periods.
CREATE OR REPLACE VIEW v_kpi_04_positive_feedback AS
WITH agg AS (
  SELECT
    grain, period_label, period_start, period_end, is_complete_period,
    dim_user_group, dim_model_id, dim_app_version,
    count_if(feedback = 1)         AS positive,
    count_if(feedback IS NOT NULL) AS rated
  FROM v_query_period
  GROUP BY grain, period_label, period_start, period_end, is_complete_period,
           dim_user_group, dim_model_id, dim_app_version
)
SELECT
  'KPI-04'                                    AS kpi_id,
  grain, period_label, period_start, period_end, is_complete_period,
  dim_user_group                              AS user_group,
  dim_model_id                                AS model_id,
  dim_app_version                             AS app_version,
  CAST(positive AS double)                    AS numerator,
  CAST(rated AS double)                       AS denominator,
  CAST(positive AS double) / nullif(rated, 0) AS kpi_value,
  rated                                       AS sample_size,
  CAST(30 AS bigint)                          AS min_sample,
  'week'                                      AS target_grain,
  '>='                                        AS target_operator,
  0.75e0                                      AS target_value,
  (grain = 'week' AND is_complete_period AND rated >= 30) AS is_evaluated,
  (grain = 'week' AND is_complete_period AND rated >= 30
     AND CAST(positive AS double) / rated < 0.75)         AS target_breached
FROM agg
