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
- [x] Synthetic sample data
- [ ] Pipeline (S3, Glue, Athena)
- [ ] QuickSight dashboard
- [ ] Row-level security and refresh
- [ ] UAT and governance notes

## Data
Only synthetic data. No personal data.

### Synthetic sample data
The generator creates 90 days of query logs (2026-08-01 to 2026-10-29) for
a fictional RAG assistant, including three built-in incident scenarios
(see `docs/01-requirements.md`, section 5.3). Only one example day
(`sample-data/raw/dt=2026-08-03/`) is committed; the full set is
regenerated from a fixed seed, so it is identical on every machine.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python ingestion/generate_sample_logs.py   # writes sample-data/raw/dt=*/queries.jsonl
python ingestion/validate_sample_logs.py   # data checks + KPI results, exit code 1 on failure
```

Options: `--seed`, `--start`, `--days`, `--out`. Changing them produces a
different data set.

## Author
Luciano Sulaimon, Business Analyst / Requirements Engineer
[LinkedIn or website]
