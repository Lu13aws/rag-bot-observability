-- KPI-07 Query volume: count(query_id). No target (context KPI).
CREATE OR REPLACE VIEW v_kpi_07_query_volume AS
SELECT
  'KPI-07'                     AS kpi_id,
  grain, period_label, period_start, period_end, is_complete_period,
  CAST(NULL AS double)         AS numerator,
  CAST(NULL AS double)         AS denominator,
  CAST(count(query_id) AS double) AS kpi_value,
  count(*)                     AS sample_size,
  CAST(NULL AS bigint)         AS min_sample,
  'day'                        AS target_grain,
  CAST(NULL AS varchar)        AS target_operator,
  CAST(NULL AS double)         AS target_value,
  false                        AS is_evaluated,
  false                        AS target_breached
FROM v_query_period
GROUP BY grain, period_label, period_start, period_end, is_complete_period
