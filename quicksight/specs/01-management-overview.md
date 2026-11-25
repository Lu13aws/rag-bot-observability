# Dashboard sheet: Management overview

> **Status: Specification, not built yet.** This document describes the
> planned QuickSight sheet for story S3.2.1 (#26). It will be built during
> the QuickSight free trial (Sprint 3) and updated to reflect what was
> actually implemented.

## Purpose

Give management the status of all KPIs for one period at a glance: which
targets are met, which are breached, and how cost and volume develop.

- Stakeholder: Management (`docs/01-requirements.md`, section 2)
- Requirements: FR-01, FR-02, FR-03, FR-04, FR-05, NFR-04
- KPIs: KPI-01 to KPI-07 (`docs/02-kpi-catalog.md`)

## Data

- Dataset: Athena view `v_kpi_all`, imported into SPICE.
- QuickSight does **not** recalculate any KPI. Every value shown is a
  precomputed row of `v_kpi_all`, so the KPI catalog stays the only place
  where formulas are defined (NFR-04).
- One row per KPI, grain, period and dimension combination
  (`user_group`, `model_id`, `app_version`, each including `all`).

## Controls

| Control | Values | Default | Requirement |
|---|---|---|---|
| Time grain | day, week, month | week | FR-02 |
| Period | `period_label` of the selected grain | 2026-W43 | FR-01 |
| Team | team_a, team_b, all | all | FR-03, NFR-02 |
| Model | model-small, model-large, all | all | FR-03 |
| Version | 1.0.0, 1.1.0, 1.1.1, all | all | FR-03 |

- **Default period 2026-W43:** the demo data is static (2026-08-01 to
  2026-10-29), so a relative default such as "last week" would show no
  data. 2026-W43 (2026-10-19 to 2026-10-25) is the last complete ISO week;
  the following week 2026-W44 is an incomplete edge period and is not
  evaluated against targets.
- **Single selection only** for team, model and version. Multi-select or
  "Select all" would combine precomputed rows (for example adding the p95 of
  two teams) and show wrong values.
- **Guard:** a calculated field `rows_per_kpi = count(kpi_id)` must be 1 in
  every KPI tile; otherwise the tile shows "ambiguous selection" instead of
  a value.

## Visuals

Every visual title contains the KPI IDs it shows (NFR-04).

| ID | Visual | Content | KPIs | Requirement |
|---|---|---|---|---|
| V1 | KPI tiles (7) | Value of the selected period, target as subtitle. Red if `target_breached`, grey with "not evaluated" if `is_evaluated = false`. | KPI-01 to KPI-07 | FR-01, FR-05 |
| V2 | Target status table | KPI, value, target, `sample_size`, minimum sample, evaluated, breached | KPI-01 to KPI-06 | FR-01, FR-05 |
| V3 | Breaches over time | Heatmap KPI x period of the selected grain, coloured by `target_breached` | KPI-01 to KPI-06 | FR-04, FR-05 |
| V4 | Cost and volume | Bars: query volume, line: cost per query, per month; October marked as incomplete | KPI-06, KPI-07 | FR-04 |
| V5 | Trends | Small multiples: one line per KPI over the periods of the selected grain, target line from `target_value` | KPI-01 to KPI-06 | FR-04 |
| T1 | Text box "How to read" | Meaning of "not evaluated" (minimum sample, incomplete edge period), single selection of filters, model note | - | NFR-04 |

With the default selection (all/all/all), V3 shows exactly the eight
breaches of the built-in scenarios.

## Model note (text in T1 and next to the KPI-01 tile)

> KPI-01 has one target for all models. model-large is slower by design
> (median daily p95 about 7.3 s in the synthetic data), so single days above
> 8 s are expected for this model and not an incident. Model-specific
> targets would require a change of the KPI catalog.

Basis (local validator, day grain, team and version = all): median daily
p95 4,873 ms for model-small and 7,317 ms for model-large; model-large
breaches 8,000 ms on 4 days outside the latency spike.

## Acceptance (S3.2.1)

| Criterion | Check |
|---|---|
| All KPIs with time grain switch (FR-01, FR-02) | For 3 periods per grain, dashboard values equal `v_kpi_all` |
| Target breaches highlighted (FR-05) | KPI-02 on 2026-09-16 is red; a non-breaching day is not |
| Cost per query and query volume included (KPI-06, KPI-07) | V1 and V4 |
| Values match the Athena reference views | `rows_per_kpi = 1` in all tiles; 5 sample values compared with Athena |

## Open points

- Row-level security (S3.3.1): readers of Team A or Team B do not see rows
  with `user_group = all`, so the default team filter would show no data
  for them. To be solved in S3.3.1 (e.g. a separate team sheet).
