# QuickSight trial checklist

> **Plan.** Nothing in this checklist has been executed yet. Boxes are
> ticked only when a step has actually been done.

- Trial start: 2026-12-09 (start of Sprint 3)
- Trial length: 30 days (until about 2027-01-07)
- **Cancellation no later than 2027-01-03**
- All QuickSight actions are done by the author in the console. Commands that
  read from or export QuickSight are run only after explicit approval.

## Before the trial (until 2026-12-08, repository only)

- [ ] Specifications 01 to 05 in `quicksight/specs/` reviewed
- [ ] `quicksight/rls/rls-rules.csv` and `team-defaults.csv` reviewed
- [ ] `python ingestion/compare_kpis.py` -> "Mismatches: none"
- [ ] `bash infra/09_tag_coverage.sh` -> 0 untagged cost-relevant resources
- [ ] Three e-mail aliases for the readers chosen (not stored in the repository)
- [ ] Calendar entries: 2027-01-02 export of dashboard definitions and
      screenshots (S5.2.1); 2027-01-03 cancellation at the latest

## Day 1 (2026-12-09, QuickSight console)

- [ ] 7. Subscribe to the QuickSight **Enterprise trial** in **eu-central-1**.
      **Read the AWS confirmation screen yourself** before confirming: it
      must say Enterprise trial and must not include the 250 USD per month
      infrastructure fee. **If in doubt, cancel the sign-up.** Do not add
      Pro users, Q or topics. Write down the trial end date.
- [ ] 8. Security & permissions: allow Athena, grant access to the project
      bucket incl. write access to `athena-results/`
- [ ] 9. Data source Athena, workgroup `rag-bot-observability`; connection
      test succeeds
- [ ] 10. Datasets `v_kpi_all` and `v_failures_by_type` in SPICE; rows
      13,680 and 2,176
- [ ] 11. Refresh schedule daily 07:00 / 07:05 Europe/Zurich, e-mail on
      failure (`specs/05-refresh.md`)
- [ ] 12. Groups `team-a`, `team-b`, `management`; three readers invited,
      **each in exactly one group**; author in `management` (test T7)
- [ ] 13. Upload `rls_rules` and apply it to **both** datasets; upload
      `team_defaults`
- [ ] 14. Test T0: dynamic default for `pTeam`; if not available, use the
      fallback text box
- [ ] 15. **Test T4 (most important):** a reader without a group sees no data.
      If this fails, stop and do not continue with readers.

## Sprint 3 (2026-12-09 to 2026-12-22)

- [ ] 16. Management sheet per `specs/01-management-overview.md`, accepted (#26)
- [ ] 17. Operations sheet per `specs/02-operations.md`, incl. the Team A
      check that both datasets show the same selection (#27)
- [ ] 18. AI engineering sheet per `specs/03-ai-engineering.md` (#28)
- [ ] 19. Row-level security tests T1 to T7 per `specs/04-access-and-rls.md` (#30)
- [ ] 20. Refresh history "Completed", rows 13,680 / 2,176 (#31)
- [ ] 21. After each step: update the spec to what was actually built, set
      its status to "Implemented", then set the story to Done
- [ ] 22. Weekly: project budget and Cost Explorer; QuickSight 0 USD during
      the trial, all other project cost below 1 USD (NFR-03)

## Before the cancellation (2027-01-02 to 2027-01-03 at the latest)

- [ ] 23. UAT completed with protocol (#34)
- [ ] 24. Dashboard definitions exported with `describe-dashboard-definition`
      (only after approval) and screenshots stored in `quicksight/` (#47)
- [ ] 25. QuickSight cancelled, **no later than 2027-01-03** (#47)
- [ ] 26. Billing shows no QuickSight charges after the cancellation (NFR-03)
