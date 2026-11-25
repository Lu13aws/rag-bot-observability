-- FR-06: failed queries per period, dimension combination, status and
-- error_type. The counts are additive: per period and combination, the sum
-- of failed_queries equals the numerator of KPI-02.
CREATE OR REPLACE VIEW v_failures_by_type AS
SELECT
  grain, period_label, period_start, period_end, is_complete_period,
  dim_user_group            AS user_group,
  dim_model_id              AS model_id,
  dim_app_version           AS app_version,
  status,
  coalesce(error_type, '-') AS error_type,
  count(*)                  AS failed_queries
FROM v_query_period
WHERE status IN ('error', 'timeout')
GROUP BY grain, period_label, period_start, period_end, is_complete_period,
         dim_user_group, dim_model_id, dim_app_version, status, error_type
