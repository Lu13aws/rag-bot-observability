# SPICE refresh

> **Status: Specification, not built yet.** This document describes the
> planned refresh setup for story S3.3.2 (#31). It will be set up during the
> QuickSight free trial (Sprint 3) and updated to reflect what was actually
> implemented.

## Purpose

Dashboard users work with current numbers: all queries up to the end of the
previous day are available by 08:00 Europe/Zurich (NFR-01).

- Requirement: NFR-01
- Demo data is static (2026-08-01 to 2026-10-29). The daily refresh is set up
  to show the mechanism; the values do not change.

## Refresh schedule

| Dataset | Refresh | Schedule | Reason |
|---|---|---|---|
| `v_kpi_all` | Full refresh | Daily 07:00, time zone Europe/Zurich | 13,680 rows; an incremental refresh would only add complexity |
| `v_failures_by_type` | Full refresh | Daily 07:05, Europe/Zurich | Offset so the two Athena queries do not run at the same time |
| `rls_rules`, `team_defaults` | None | - | File uploads; changed only by uploading the files from `quicksight/rls/` again |

- Option "Email owners when a refresh fails" is enabled on both datasets;
  this is the monitoring for NFR-01.
- SPICE capacity: 10 GB are included per author; both datasets together use
  far less than 1 MB.

## Text box on every sheet

> Demo data is static (2026-08-01 to 2026-10-29). The daily refresh is set
> up to show the mechanism; values do not change.

## Cost

Each refresh runs two Athena queries, billed with the 10 MB minimum each:
about 0.0001 USD per day, about 0.003 USD over the trial. The queries run in
the tagged workgroup, so the cost is part of the project budget (NFR-03).

## Acceptance (S3.3.2)

| Criterion | Check |
|---|---|
| Daily refresh before 08:00 Europe/Zurich (NFR-01) | The schedule of both datasets shows daily 07:00 / 07:05 Europe/Zurich |
| Refresh history shows a successful run | On the morning after setup, the history of both datasets shows "Completed" with 13,680 and 2,176 rows |
| Note "demo data is static" documented | Text box on every sheet, and this document |
