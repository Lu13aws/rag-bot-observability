# Dashboard sheet: Operations

> **Status: Specification, not built yet.** This document describes the
> planned QuickSight sheet for story S3.2.2 (#27). It will be built during
> the QuickSight free trial (Sprint 3) and updated to reflect what was
> actually implemented.

## Purpose

Help operations detect incidents quickly: daily response time and error
rate against their targets, and what kind of failures caused a breach.

- Stakeholder: Operations (`docs/01-requirements.md`, section 2)
- Requirements: FR-03, FR-04, FR-05, FR-06, NFR-04
- KPIs: KPI-01, KPI-02, KPI-07 (`docs/02-kpi-catalog.md`)

## Data

| Dataset | Source | Used for |
|---|---|---|
| KPIs | Athena view `v_kpi_all`, SPICE | KPI-01, KPI-02, KPI-07 at day grain |
| Failures | Athena view `v_failures_by_type`, SPICE | FR-06: failed queries per day, `status` and `error_type` |

- QuickSight does **not** recalculate any KPI (NFR-04). The failure counts
  are additive; per day and selection their sum equals the KPI-02 numerator.
- **Both datasets must show the same selection.** Team, model and version
  are QuickSight **parameters**; each parameter is bound to a filter on
  *both* datasets. A filter on only one dataset would make the failure chart
  show a different slice than the KPI lines.

## Controls

| Control | Values | Default | Reason |
|---|---|---|---|
| Time grain | day (fixed, hidden filter) | day | Operations evaluates KPI-01 and KPI-02 per day. The grain switch (FR-02) is on the management sheet. |
| Date range (`period_start`) | 2026-08-01 to 2026-10-29 | whole data period | Both incident scenarios must be visible on the time axis. |
| Team | team_a, team_b, all | all | FR-03, NFR-02 |
| Model | model-small, model-large, all | all | FR-03 |
| Version | 1.0.0, 1.1.0, 1.1.1, all | all | FR-03 |

Single selection only for team, model and version (see the management
sheet: multi-select would combine precomputed rows).

## Visuals

Every visual title contains the KPI IDs it shows (NFR-04).

| ID | Visual | Content | KPIs | Requirement |
|---|---|---|---|---|
| O1 | Line, daily | p95 latency with target line 8,000 ms. Points red if `target_breached`, hollow grey if not evaluated (< 100 successful queries). Tooltip: `sample_size`. | KPI-01 | FR-04, FR-05 |
| O2 | Line, daily | Error rate with target line 2 %, markers as in O1 (< 200 queries). Tooltip: numerator, denominator. | KPI-02 | FR-04, FR-05 |
| O3 | Stacked bars, daily | Failed queries per `status/error_type` from `v_failures_by_type` | KPI-02 | FR-06 |
| O4 | Bars, daily | Query volume; explains why weekends are not evaluated | KPI-07 | FR-04 |
| O5 | Table "Days breaching targets" | Evaluated and breached days of KPI-01 and KPI-02 with value and sample size | KPI-01, KPI-02 | FR-05 |
| T1 | Text box "How to read" | Minimum samples (100 / 200), meaning of hollow points, model note (same text as the management sheet) | - | NFR-04 |

## Expected values (local validator, selection all/all/all)

| Day | Volume | KPI-01 p95 | KPI-02 error rate | Failures by type (O3) |
|---|---|---|---|---|
| 2026-09-08 (normal) | 410 | 6,485 ms | 0.98 % | llm_api 3, retrieval 1 |
| 2026-09-15 (release 1.1.0) | 380 | 5,927 ms | 5.00 % (breach) | llm_api 16, timeout 3 |
| 2026-09-16 | 374 | 6,145 ms | 5.61 % (breach) | llm_api 19, timeout 2 |
| 2026-09-17 | 348 | 5,915 ms | 7.47 % (breach) | llm_api 26 |
| 2026-09-29 (latency spike) | 366 | 12,556 ms (breach) | 1.09 % | llm_api 2, retrieval 1, timeout 1 |

Over all 90 days: 271 failed queries (llm_api 125, llm_timeout 81,
retrieval 65). KPI-01 and KPI-02 are each evaluated on 64 of 90 days.

## Acceptance (S3.2.2)

| Criterion | Check |
|---|---|
| Daily trends for KPI-01 and KPI-02 (FR-04) | O1 and O2 show 90 daily points; the 5 days above match `v_kpi_all` |
| Breakdown by `status` and `error_type` (FR-06) | Per day, the sum in O3 equals the KPI-02 numerator in O2 |
| **Both datasets show the same selection** | Set team = team_a. On 2026-09-16 the sum in O3 is 12 (llm_api 12) and the KPI-02 numerator in O2 is 12 (223 queries, 5.38 %, breach). On 2026-09-08: 3 and 3 (238 queries, 1.26 %). If the numbers differ, a parameter is not bound to both datasets. |
| Incident scenarios visible | 2026-09-15 to 09-17 red in O2 with an llm_api increase in O3; 2026-09-29 to 10-01 red in O1 |

## Open points

- Row-level security (S3.3.1): the rules must be applied to **both**
  datasets (`v_kpi_all` and `v_failures_by_type`); both have the column
  `user_group`.
- As on the management sheet, the default team filter `all` shows no data
  for Team A or Team B readers (to be solved in S3.3.1).
