# User acceptance test (UAT)

> **Status: Draft, not executed.** Test cases for story S4.1.1 (#34). They
> are executed during the QuickSight free trial and must be completed before
> 2027-01-03. The columns "Result" and "Evidence" are filled in only during
> execution.

## Scope

All functional and non-functional requirements of
`docs/01-requirements.md` (FR-01 to FR-06, NFR-01 to NFR-05), tested on the
QuickSight dashboard and the Athena reference views.

## Rules

- Expected values come from the local validator
  (`ingestion/validate_sample_logs.py`) and the specifications in
  `quicksight/specs/`. Default selection: team, model and version = `all`.
- Tolerances: `docs/01-requirements.md`, section 3.1 (latency ±50 ms;
  ratios and cost ±1 % relative; error rate alternatively ±0.2 percentage
  points; query volume and counts exact).
- A test passes only if every expected value is met. A deviation is recorded
  with its cause; values are never adjusted to make a test pass.

## Entry criteria

- `python ingestion/compare_kpis.py` -> "Mismatches: none"
- `bash infra/09_tag_coverage.sh` -> 0 untagged cost-relevant resources
- Sheets built per `quicksight/specs/01` to `05`; specs updated to what was
  built
- Readers set up per `quicksight/specs/04-access-and-rls.md`

## Test cases

| ID | Requirement | Steps | Expected | Result | Evidence |
|---|---|---|---|---|---|
| UAT-01 | FR-01 All KPIs for a selected period | Management sheet, grain week, period 2026-W43 | KPI-01 6,288 ms · KPI-02 0.89 % · KPI-03 6.25 % · KPI-04 87.58 % · KPI-05 7.13 % · KPI-06 0.007983 USD · KPI-07 2,146. KPI-03 to KPI-05 evaluated, none breached; KPI-01, KPI-02, KPI-06 not evaluated at week grain | | |
| UAT-02 | FR-02 Time grain switch | Management sheet: (a) day 2026-09-16, (b) week 2026-W38, (c) month 2026-09 | (a) KPI-01 6,145 ms, KPI-02 5.61 % (breach), KPI-07 374 · (b) KPI-03 5.62 %, KPI-04 87.90 %, KPI-05 7.60 %, KPI-07 2,066 · (c) KPI-06 0.008079 USD (evaluated), KPI-07 9,302 | | |
| UAT-03 | FR-03 Filters model and version | AI engineering sheet, model = model-small, week 2026-W42; Operations sheet, version = 1.1.0, day 2026-09-15 | W42 model-small: KPI-03 25.20 % (breach), KPI-04 70.83 % (breach) · 2026-09-15 version 1.1.0: KPI-02 5.00 % (breach) | | |
| UAT-04 | FR-04 Trends | Operations sheet O1, O2; AI engineering sheet A1 to A3 | 90 daily points in O1 and O2; 14 weekly points in A1 to A3 (W31 and W44 marked as not evaluated) | | |
| UAT-05 | FR-05 Highlight target breaches | Operations sheet O1, O2 | KPI-02 2026-09-16 red; KPI-02 2026-09-08 not red (0.98 %); KPI-01 2026-08-01 grey "not evaluated" (5,906 ms, fewer than 100 successful queries); KPI-01 2026-09-29 red (12,556 ms) | | |
| UAT-06 | FR-06 Failure breakdown | Operations sheet O3: (a) team all, day 2026-09-16; (b) team = team_a, same day | (a) llm_api 19, timeout 2, sum 21 = KPI-02 numerator · (b) llm_api 12, sum 12 = KPI-02 numerator in O2 (both datasets show the same selection) | | |
| UAT-07 | NFR-01 Data freshness | Dataset settings and refresh history of `v_kpi_all` and `v_failures_by_type` | Daily refresh 07:00 / 07:05 Europe/Zurich; last run "Completed" with 13,680 / 2,176 rows; text box "demo data is static" on every sheet | | |
| UAT-08 | NFR-02 Row-level security | Tests T0 to T7 in `quicksight/specs/04-access-and-rls.md` | All tests pass; **T4 (reader without group sees no data) is mandatory**. Team A: September volume 5,620; Team B: 3,682; Management: 9,302 | | |
| UAT-09 | NFR-03 Cost | Project budget, Cost Explorer filtered on `Project`, `infra/09_tag_coverage.sh` | Budget alerts in state OK; tag-filtered month-to-date cost ≤ 50 USD; QuickSight 0 USD during the trial; tag coverage exit code 0 | | |
| UAT-10 | NFR-04 Traceability | Review all visual titles; run `ingestion/compare_kpis.py` | Every visual names its KPI IDs; compare_kpis: "Mismatches: none" | | |
| UAT-11 | NFR-05 Data protection | Search the repository for credentials, account IDs and e-mail addresses; check `quicksight/rls/*.csv` and `quicksight/export/` | No findings; RLS files contain group names only | | |

## Exit criteria

- All test cases pass, or a deviation is documented with its cause and an
  accepted decision.
- UAT completed before 2027-01-03; then the dashboard definitions are
  exported (`infra/12_quicksight_export.sh`) and QuickSight is cancelled.

## Protocol

| Date | Tester | Test cases | Result | Notes |
|---|---|---|---|---|
| | | | | |
