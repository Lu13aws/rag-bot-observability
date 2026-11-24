# rag-bot-observability

Requirements-first KPI monitoring for a RAG assistant on AWS: S3, Glue, Athena and QuickSight dashboards.

> Status: work in progress

## Goal
Show how business needs for an AI bot are turned into clear reporting
requirements, a KPI catalog and management dashboards. The monitored
system is a fictional RAG assistant inspired by my own RAG platform [link].
All data is synthetic.

## Approach
1. Requirements and stakeholder needs: `docs/01-requirements.md`
2. KPI definitions: `docs/02-kpi-catalog.md`
3. Data pipeline: logs -> S3 -> Glue -> Athena
4. Dashboards in Amazon QuickSight
5. Validation and acceptance testing

## Planned architecture
[Logs of RAG platform] -> S3 (raw) -> Glue ETL (Parquet) -> Athena -> QuickSight

## Planned KPIs
Response time (p95), error rate, share of queries without sources,
positive feedback, feedback rate, cost per query, query volume.

## Roadmap
- [x] Requirements and KPI templates
- [x] Fill in requirements and KPI targets
- [ ] Synthetic sample data
- [ ] Pipeline (S3, Glue, Athena)
- [ ] QuickSight dashboard
- [ ] Row-level security and refresh
- [ ] UAT and governance notes

## Data
Only synthetic or own test data. No personal data.

## Author
Luciano Sulaimon, Business Analyst / Requirements Engineer
[LinkedIn or website]
