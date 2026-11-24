-- Acceptance check for S2.3.1. Expected: 27548 rows, 27548 unique query_id,
-- 90 days from 2026-08-01 to 2026-10-29, no null event_ts.
SELECT
  count(*)                                        AS row_count,
  count(DISTINCT query_id)                        AS unique_query_ids,
  count(DISTINCT dt)                              AS days,
  min(dt)                                         AS first_day,
  max(dt)                                         AS last_day,
  count_if(event_ts IS NULL)                      AS null_event_ts
FROM rag_query_log
