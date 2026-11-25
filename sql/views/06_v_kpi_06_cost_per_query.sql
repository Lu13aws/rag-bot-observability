-- KPI-06 Cost per query:
--   sum(tokens_in / 1000 * price_in_per_1k + tokens_out / 1000 * price_out_per_1k)
--   / count(all queries)
-- Price row: same model_id, latest valid_from on or before the query date.
-- LEFT JOIN keeps queries without a price in the denominator; they are
-- counted in unpriced_queries as a data quality signal.
-- The price rank is partitioned per query AND dimension combination, because
-- v_query_period contains each query once per combination.
-- Target: <= 0.02 USD, evaluated per month (complete periods only).
CREATE OR REPLACE VIEW v_kpi_06_cost_per_query AS
WITH priced AS (
  SELECT
    q.grain, q.period_label, q.period_start, q.period_end, q.is_complete_period,
    q.dim_user_group, q.dim_model_id, q.dim_app_version, q.query_id,
    CAST(q.tokens_in AS double)  / 1000 * CAST(p.price_in_per_1k AS double)
      + CAST(q.tokens_out AS double) / 1000 * CAST(p.price_out_per_1k AS double) AS cost_usd,
    row_number() OVER (
      PARTITION BY q.grain, q.query_id, q.dim_user_group, q.dim_model_id, q.dim_app_version
      ORDER BY p.valid_from DESC) AS price_rank
  FROM v_query_period q
  LEFT JOIN model_pricing p
    ON p.model_id = q.model_id AND p.valid_from <= q.query_date
),
agg AS (
  SELECT
    grain, period_label, period_start, period_end, is_complete_period,
    dim_user_group, dim_model_id, dim_app_version,
    sum(cost_usd)              AS total_cost_usd,
    count(*)                   AS total,
    count_if(cost_usd IS NULL) AS unpriced_queries
  FROM priced
  WHERE price_rank = 1
  GROUP BY grain, period_label, period_start, period_end, is_complete_period,
           dim_user_group, dim_model_id, dim_app_version
)
SELECT
  'KPI-06'                          AS kpi_id,
  grain, period_label, period_start, period_end, is_complete_period,
  dim_user_group                    AS user_group,
  dim_model_id                      AS model_id,
  dim_app_version                   AS app_version,
  total_cost_usd                    AS numerator,
  CAST(total AS double)             AS denominator,
  total_cost_usd / nullif(total, 0) AS kpi_value,
  total                             AS sample_size,
  CAST(NULL AS bigint)              AS min_sample,
  'month'                           AS target_grain,
  '<='                              AS target_operator,
  0.02e0                            AS target_value,
  (grain = 'month' AND is_complete_period)                                   AS is_evaluated,
  (grain = 'month' AND is_complete_period AND total_cost_usd / total > 0.02) AS target_breached,
  unpriced_queries
FROM agg
