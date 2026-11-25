# Access control: row-level security and team defaults

> **Status: Specification, not built yet.** This document describes the
> planned access model for story S3.3.1 (#30). It will be set up during the
> QuickSight free trial (Sprint 3) and updated to reflect what was actually
> implemented.

## Purpose

Each team lead sees only the data of their own team; management sees all
data (need-to-know principle).

- Stakeholders: Team A / Team B leads, Management
  (`docs/01-requirements.md`, section 2)
- Requirement: NFR-02

## Groups and users

| QuickSight group | Members | Role |
|---|---|---|
| `team-a` | 1 reader | Team A lead |
| `team-b` | 1 reader | Team B lead |
| `management` | 1 reader and the author | Management |

- **Every reader belongs to exactly one group.** QuickSight combines the
  rules of all groups a user belongs to; a reader in `team-a` and
  `management` would see all data.
- The author must be in `management`; otherwise the author sees no data once
  row-level security is active.
- Reader accounts use e-mail aliases of the author. **E-mail addresses are
  not stored in this repository.**

## Row-level security rules

File: [`quicksight/rls/rls-rules.csv`](../rls/rls-rules.csv), uploaded to
QuickSight as dataset `rls_rules` (file upload).

| GroupName | user_group | Sees |
|---|---|---|
| `team-a` | `team_a` | rows of Team A only |
| `team-b` | `team_b` | rows of Team B only |
| `management` | *(empty = all values)* | all rows, incl. `all` |

- Applied to **both** datasets: `v_kpi_all` and `v_failures_by_type` (both
  have the column `user_group`).
- Users that are not covered by a rule see no data.
- **Why team readers must not see `all` rows:** the overall values would
  reveal the other team. Example (query volume, September 2026): Team A
  5,620, all 9,302, so Team B = 9,302 - 5,620 = 3,682.

## Default team per user

Problem: the team filter defaults to `all`. After row-level security,
Team A and Team B readers have no `all` rows, so their sheets would open
empty.

Solution: **dynamic default value** for the team parameter `pTeam`.

- File: [`quicksight/rls/team-defaults.csv`](../rls/team-defaults.csv),
  uploaded as dataset `team_defaults`.
- Mapping: `team-a` -> `team_a`, `team-b` -> `team_b`, `management` -> `all`;
  static fallback `all`.
- The team control takes its values from the dataset field `user_group`, so
  after row-level security a team reader can only select their own team.
- **To be confirmed first in the trial (test T0).** If dynamic defaults are
  not available, the fallback is a text box on every sheet: "Team leads:
  select your team in the Team filter."

Rejected: separate sheets per team (duplicated visuals to maintain); a text
box only (sheets still open empty).

## Setup steps (QuickSight console, during the trial)

1. Create the groups `team-a`, `team-b`, `management`.
2. Invite three readers (e-mail aliases) and add each to exactly one group;
   add the author to `management`.
3. Upload `rls-rules.csv` as dataset `rls_rules`.
4. On `v_kpi_all` and on `v_failures_by_type`: Row-level security ->
   select `rls_rules` -> activate.
5. Upload `team-defaults.csv` as dataset `team_defaults`.
6. Parameter `pTeam`: dynamic default from `team_defaults`, fallback `all`;
   the team control lists the values of the field `user_group`.

## Tests (NFR-02)

Expected values from the local validator. T4 is the most important test:
access must be denied by default.

| Test | Signed in as | Expected |
|---|---|---|
| T0 | Author | Dynamic default for `pTeam` can be configured. If not: fallback text box. |
| T1 | Team A reader | Team control shows only `team_a`, default `team_a`. Query volume September 5,620. 2026-09-16: KPI-02 5.38 %, red; failure sum in O3 is 12. |
| T2 | Team B reader | Only `team_b`. Query volume September 3,682. 2026-09-16: KPI-02 5.96 %, grey "not evaluated" (fewer than 200 queries); failure sum in O3 is 9. |
| T3 | Management reader | `team_a`, `team_b` and `all` selectable, default `all`. Query volume September 9,302. 2026-09-16: KPI-02 5.61 %, red. |
| **T4** | **Reader without a group** (temporarily removed from their group) | **No data on any sheet and in both datasets.** |
| T5 | Team A reader | No row with `team_b` or `all` is selectable or visible, also not in tables or tooltips. |
| T6 | All readers | Values of T1 to T3 equal `v_kpi_all` with the same filter (Athena values are verified by `ingestion/compare_kpis.py`). |
| T7 | Author | Each reader is a member of exactly one group (group membership list). |

## Cost

Readers are free during the trial (up to 25 users). No cost after the
cancellation.
