# KPI Catalog

Single source of truth for all KPI definitions in this project. Dashboards
and SQL queries must use the definitions in this file only.

## General calculation rules

- **Time zone:** all periods use Europe/Zurich local time. `event_ts` is
  stored in UTC and converted for reporting.
- **Periods:** day; ISO week (Monday to Sunday); calendar month.
- **Aggregation:** every KPI is recalculated from row level for each period.
  Daily values are never averaged into weekly or monthly values, because
  averaging ratios or percentiles gives wrong results.
- **Populations:** "all queries" = all rows of `rag_query_log` in the period;
  "successful queries" = rows with `status = 'success'`.
- **Division by zero:** the KPI is `null` and shown as "no data".
- **Incomplete edge periods:** a week or month that is only partly covered
  by the data period (at its start or end) is shown, but not evaluated
  against the target. Example: the data starts on a Saturday, so the first
  ISO week contains only two weekend days and is not representative.
- **p95 method:** nearest rank, i.e. the smallest `latency_ms` value such that
  at least 95 % of the values are less than or equal to it. QuickSight uses
  `percentileDisc(latency_ms, 95)`. The Athena reference query calculates the
  exact nearest rank with a window function; `approx_percentile` is not used
  for acceptance because it is an approximation.
- **Acceptance tolerance:** a dashboard value is correct if its deviation from
  the Athena reference query is within:
  - latency (KPI-01): ±50 ms;
  - ratios and cost (KPI-02 to KPI-06): ±1 % relative;
  - error rate (KPI-02): alternatively ±0.2 percentage points absolute. A
    KPI-02 value passes if it meets at least one of the two limits.
  - query volume (KPI-07): exact match.

## KPIs

| ID | KPI | Definition / formula | Data source | Target grain | Target | Owner | Notes |
|---|---|---|---|---|---|---|---|
| KPI-01 | Response time (p95) | p95 of `latency_ms` over successful queries | `rag_query_log.latency_ms`, `status` | Day | < 8,000 ms | Operations | Errors and timeouts are excluded on purpose; they are covered by KPI-02. |
| KPI-02 | Error rate | count(`status` in ('error', 'timeout')) / count(all queries) | `rag_query_log.status` | Day | < 2 % | Operations | Not evaluated against the target if fewer than 200 queries in the period. |
| KPI-03 | No-source share | count(successful queries with `sources_count = 0`) / count(successful queries) | `rag_query_log.sources_count`, `status` | Week | < 10 % | AI Engineering | |
| KPI-04 | Positive feedback | count(`feedback = 1`) / count(`feedback` is not null) | `rag_query_log.feedback` | Week | ≥ 75 % | AI Engineering | Not evaluated against the target if fewer than 30 rated queries in the period. |
| KPI-05 | Feedback rate | count(`feedback` is not null) / count(all queries) | `rag_query_log.feedback` | Week | ≥ 5 % | AI Engineering | |
| KPI-06 | Cost per query | sum(`tokens_in` / 1000 × `price_in_per_1k` + `tokens_out` / 1000 × `price_out_per_1k`) / count(all queries) | `rag_query_log.tokens_in`, `tokens_out`, `model_id`; `model_pricing` | Month | ≤ 0.02 USD | Management | LLM token cost only. Price row = same `model_id`, latest `valid_from` on or before the query date. Prices are fictional. |
| KPI-07 | Query volume | count(`query_id`) | `rag_query_log.query_id` | Day | none (context) | Management | |

All KPIs are available per day, week and month (see FR-02 in
`docs/01-requirements.md`). "Target grain" is the period at which the target
is evaluated.

## Target rationale

Targets are assumptions for a typical internal RAG assistant, not external
benchmarks.

- **KPI-01:** retrieval plus LLM generation usually takes a few seconds; 8 s
  keeps the slowest 5 % acceptable for a chat interface.
- **KPI-02:** at most 1 in 50 queries fails, a common expectation for an
  internal tool. The 200-query minimum excludes low-volume days (e.g.
  weekends with about 80 queries), where 2 failed queries already mean 2.5 %
  and the target would be breached by chance.
- **KPI-03:** a higher share points to gaps in the knowledge base or weak
  retrieval.
- **KPI-04:** a clear majority of rated answers is positive; the 30-rating
  minimum avoids judging on a handful of votes.
- **KPI-05:** explicit feedback is voluntary and rare; below 5 % KPI-04 is not
  reliable.
- **KPI-06:** matches the fictional prices in `model_pricing` (see
  `docs/01-requirements.md`, section 5.1) at about 2,000 input and 300 output
  tokens per query, with a buffer.
