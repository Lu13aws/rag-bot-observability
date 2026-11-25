-- All KPIs in one long table with identical columns: one row per KPI, grain,
-- period and dimension combination (user_group, model_id, app_version, each
-- incl. 'all'). Used for the validator comparison and as the QuickSight
-- dataset. Row-level security filters on user_group (NFR-02).
CREATE OR REPLACE VIEW v_kpi_all AS
SELECT kpi_id, grain, period_label, period_start, period_end, is_complete_period,
       user_group, model_id, app_version,
       numerator, denominator, kpi_value, sample_size, min_sample,
       target_grain, target_operator, target_value, is_evaluated, target_breached
FROM v_kpi_01_latency_p95
UNION ALL SELECT kpi_id, grain, period_label, period_start, period_end, is_complete_period,
       user_group, model_id, app_version,
       numerator, denominator, kpi_value, sample_size, min_sample,
       target_grain, target_operator, target_value, is_evaluated, target_breached
FROM v_kpi_02_error_rate
UNION ALL SELECT kpi_id, grain, period_label, period_start, period_end, is_complete_period,
       user_group, model_id, app_version,
       numerator, denominator, kpi_value, sample_size, min_sample,
       target_grain, target_operator, target_value, is_evaluated, target_breached
FROM v_kpi_03_no_source_share
UNION ALL SELECT kpi_id, grain, period_label, period_start, period_end, is_complete_period,
       user_group, model_id, app_version,
       numerator, denominator, kpi_value, sample_size, min_sample,
       target_grain, target_operator, target_value, is_evaluated, target_breached
FROM v_kpi_04_positive_feedback
UNION ALL SELECT kpi_id, grain, period_label, period_start, period_end, is_complete_period,
       user_group, model_id, app_version,
       numerator, denominator, kpi_value, sample_size, min_sample,
       target_grain, target_operator, target_value, is_evaluated, target_breached
FROM v_kpi_05_feedback_rate
UNION ALL SELECT kpi_id, grain, period_label, period_start, period_end, is_complete_period,
       user_group, model_id, app_version,
       numerator, denominator, kpi_value, sample_size, min_sample,
       target_grain, target_operator, target_value, is_evaluated, target_breached
FROM v_kpi_06_cost_per_query
UNION ALL SELECT kpi_id, grain, period_label, period_start, period_end, is_complete_period,
       user_group, model_id, app_version,
       numerator, denominator, kpi_value, sample_size, min_sample,
       target_grain, target_operator, target_value, is_evaluated, target_breached
FROM v_kpi_07_query_volume
