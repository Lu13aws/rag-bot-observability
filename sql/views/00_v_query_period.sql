-- Base view: one row per query, time grain (day, ISO week, month) and
-- dimension combination.
-- Periods are derived from dt, the local date in Europe/Zurich (assumption
-- A-3), so no time zone conversion is needed in the KPI views.
-- Dimensions: each query appears once with its own value and once with 'all'
-- for user_group, model_id and app_version (2 x 2 x 2 = 8 combinations).
-- The KPI views can therefore precompute exact values (incl. p95 and ratios)
-- for every filter combination; rows with 'all' in every dimension are the
-- overall KPIs (FR-03, NFR-02).
-- is_complete_period: the period is fully covered by the data period
-- (KPI catalog, rule "Incomplete edge periods").
CREATE OR REPLACE VIEW v_query_period AS
WITH bounds AS (
  SELECT min(date(dt)) AS data_start, max(date(dt)) AS data_end
  FROM rag_query_log
),
with_grain AS (
  SELECT
    l.*,
    date(l.dt) AS query_date,
    g.grain,
    ug.dim_user_group,
    md.dim_model_id,
    av.dim_app_version,
    CASE g.grain
      WHEN 'day'  THEN date(l.dt)
      WHEN 'week' THEN date_trunc('week', date(l.dt))   -- ISO week starts on Monday
      ELSE             date_trunc('month', date(l.dt))
    END AS period_start
  FROM rag_query_log l
  CROSS JOIN (VALUES 'day', 'week', 'month') AS g (grain)
  CROSS JOIN UNNEST(ARRAY[l.user_group, 'all'])  AS ug (dim_user_group)
  CROSS JOIN UNNEST(ARRAY[l.model_id, 'all'])    AS md (dim_model_id)
  CROSS JOIN UNNEST(ARRAY[l.app_version, 'all']) AS av (dim_app_version)
),
with_period AS (
  SELECT
    w.*,
    CASE w.grain
      WHEN 'day'  THEN w.period_start
      WHEN 'week' THEN date_add('day', 6, w.period_start)
      ELSE             date_add('day', -1, date_add('month', 1, w.period_start))
    END AS period_end,
    CASE w.grain
      WHEN 'day'  THEN w.dt
      WHEN 'week' THEN format('%d-W%02d', year_of_week(w.query_date), week_of_year(w.query_date))
      ELSE             date_format(w.query_date, '%Y-%m')
    END AS period_label
  FROM with_grain w
)
SELECT
  p.*,
  (p.period_start >= b.data_start AND p.period_end <= b.data_end) AS is_complete_period
FROM with_period p
CROSS JOIN bounds b
