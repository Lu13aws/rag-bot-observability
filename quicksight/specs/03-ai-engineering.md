# Dashboard sheet: AI engineering

> **Status: Specification, not built yet.** This document describes the
> planned QuickSight sheet for story S3.2.3 (#28). It will be built during
> the QuickSight free trial (Sprint 3) and updated to reflect what was
> actually implemented.

## Purpose

Give AI engineering weekly quality signals per model and release: how often
answers have no source, how users rate answers and how often they rate at
all.

- Stakeholder: AI Engineering (`docs/01-requirements.md`, section 2)
- Requirements: FR-03, FR-04, FR-05, NFR-04
- KPIs: KPI-03, KPI-04, KPI-05 (`docs/02-kpi-catalog.md`)

## Data

- Dataset: Athena view `v_kpi_all`, SPICE (same dataset as the management
  sheet). QuickSight does **not** recalculate any KPI (NFR-04).

## Controls

| Control | Values | Default | Reason |
|---|---|---|---|
| Time grain | week (fixed, hidden filter) | week | Target grain of KPI-03, KPI-04 and KPI-05 |
| Date range (`period_start`) | 2026-W31 to 2026-W44 | whole data period | The knowledge gap in 2026-W42 must be visible in the trend. W31 and W44 are incomplete edge weeks and not evaluated. |
| Team | team_a, team_b, all | all | FR-03, NFR-02 |
| Model | model-small, model-large, all | all | FR-03 |
| Version | 1.0.0, 1.1.0, 1.1.1, all | all | FR-03 |

Single selection only for team, model and version (multi-select would
combine precomputed rows).

## Visuals

Every visual title contains the KPI IDs it shows (NFR-04).

| ID | Visual | Content | KPIs | Requirement |
|---|---|---|---|---|
| A1 | Line, weekly | No-source share with target line 10 %; red if breached, hollow grey if not evaluated | KPI-03 | FR-04, FR-05 |
| A2 | Line, weekly | Positive feedback with target line 75 %; hollow if fewer than 30 rated queries | KPI-04 | FR-04, FR-05 |
| A3 | Line, weekly | Feedback rate with target line 5 % | KPI-05 | FR-04, FR-05 |
| A4 | Comparison table | model-small and model-large side by side **for the same week**: KPI-03, KPI-04, KPI-05 and `sample_size`. Two visuals with their own model filter; no recalculation. | KPI-03, KPI-04, KPI-05 | FR-03 |
| A5 | Combined line | No-source share and positive feedback in one chart. Title: "Drop in positive feedback coincides with more answers without sources (KPI-03, KPI-04)". | KPI-03, KPI-04 | FR-04 |
| T1 | Text box "How to read" | See below | - | NFR-04 |

### Text for T1

- **Not evaluated:** KPI-04 needs at least 30 rated queries; W31 and W44 are
  incomplete edge weeks.
- **Comparing versions:** versions were live in different weeks. A
  comparison over the whole period mixes the effect of the version with
  everything else that happened in those weeks. Example: 1.1.1 shows a
  higher no-source share (9.15 % vs. 5.38 % for 1.0.0) only because the
  knowledge gap in W42 happened while 1.1.1 was live. Compare versions only
  in weeks without incidents. 1.1.0 was live for three days only.
- **Comparing models:** the synthetic data simulates a different latency per
  model, but the same answer quality. KPI-03, KPI-04 and KPI-05 are
  therefore almost equal for both models. This is a property of the
  simulation, not a finding about real models.
- **A5:** the link between missing sources and lower satisfaction is built
  into the synthetic data (`docs/01-requirements.md`, section 5.3: ratings
  are positive with 85 % with sources and 40 % without). A5 shows that the
  two KPIs move together; it does not prove a cause.

## Expected values (local validator)

Selection all/all/all:

| Week | KPI-03 no-source share | KPI-04 positive feedback | KPI-05 feedback rate |
|---|---|---|---|
| 2026-W38 | 5.62 % | 87.90 % | 7.60 % |
| 2026-W41 | 6.25 % | 83.43 % | 8.47 % |
| 2026-W42 | 25.57 % (breach) | 72.49 % (breach) | 8.72 % |
| 2026-W43 | 6.25 % | 87.58 % | 7.13 % |

Week 2026-W42 per selection:

| Selection | KPI-03 | KPI-04 |
|---|---|---|
| model-small | 25.20 % (breach) | 70.83 % (breach) |
| model-large | 26.49 % (breach) | 77.78 % |
| team_a | 26.30 % (breach) | 70.94 % (breach) |
| team_b | 24.48 % (breach) | 75.00 % (exactly on target, no breach) |

Whole data period per version and model (context for T1, not shown as a
visual):

| Selection | Queries | KPI-03 | KPI-04 | KPI-05 |
|---|---|---|---|---|
| 1.0.0 | 13,508 | 5.38 % | 81.40 % | 7.96 % |
| 1.1.0 | 1,102 | 5.41 % | 88.24 % | 7.71 % |
| 1.1.1 | 12,938 | 9.15 % | 81.95 % | 8.09 % |
| model-small | 19,323 | 7.06 % | 82.15 % | 7.97 % |
| model-large | 8,225 | 7.38 % | 81.38 % | 8.10 % |

## Known noise

In 2026-W34, KPI-04 breaches its target in some small selections
(model-large; team_a; and their combinations with version 1.0.0), although
no scenario is active in that week. These selections just reach the minimum
of 30 rated queries, so single ratings move the value by several percentage
points. This is documented only; the minimum sample size is not changed.

## Acceptance (S3.2.3)

| Criterion | Check |
|---|---|
| KPI-03, KPI-04 and KPI-05 per week | A1 to A3 show 14 weeks; the 4 weeks above match `v_kpi_all` |
| Filters for `model_id` and `app_version` (FR-03) | Model = model-small: W42 shows KPI-03 25.20 % and KPI-04 70.83 % |
| Knowledge gap in 2026-W42 visible | Red in A1 and A2, simultaneous change in A5 |

## Open points

- Row-level security (S3.3.1): as on the other sheets, the default team
  filter `all` shows no data for Team A or Team B readers.
