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

## Architecture

| Step | Component | Status |
|---|---|---|
| 1 | Synthetic query logs (JSON Lines, one file per day) | implemented |
| 2 | S3 `raw/` | implemented |
| 3 | Glue job: JSON to Parquet/Snappy, partitioned by `dt` | implemented |
| 4 | S3 `processed/` and Glue Data Catalog | implemented |
| 5 | Athena tables and KPI reference views (`sql/`) | implemented |
| 6 | QuickSight dashboards (SPICE, row-level security, refresh) | planned (QuickSight) |

Flow: synthetic logs -> S3 raw -> Glue (Parquet) -> S3 processed -> Athena
views -> QuickSight. The QuickSight part is specified in `quicksight/specs/`
and will be built during the QuickSight free trial.

## KPIs
Response time (p95), error rate, share of queries without sources,
positive feedback, feedback rate, cost per query, query volume.
Defined in `docs/02-kpi-catalog.md` and implemented as Athena views
(`sql/views/`); the view results match the local validator for every
period and dimension combination (`ingestion/compare_kpis.py`).

## Roadmap
- [x] Requirements and KPI templates
- [x] Fill in requirements and KPI targets
- [x] Synthetic sample data
- [x] Pipeline (S3, Glue, Athena)
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

## Pipeline (AWS)

Prerequisites: AWS CLI v2, bash (Git Bash on Windows), an AWS profile for
region `eu-central-1`. Copy `infra/config.env.example` to `infra/config.env`
(git-ignored) and fill in bucket name and alert e-mail. The account ID is
read at runtime and never stored in the repository.

Run the scripts in this order. Each script checks first whether a resource
already exists, prints every AWS command before it runs, and supports
`DRY_RUN=1` to only print the commands.

| Script | Step |
|---|---|
| `infra/00_check_identity.sh` | Show the AWS identity and its permissions (read-only) |
| `infra/01_budget.sh` | Monthly project budget filtered on the tag `Project`, e-mail alerts |
| `infra/02_s3_bucket.sh` | Private, encrypted project bucket |
| `infra/03_upload.sh` | Validate the sample data locally, then upload data and Glue script |
| `infra/04_iam_glue_role.sh` | Least-privilege IAM role for the Glue job |
| `infra/05_glue_job.sh` | Glue database and job (2 workers, 10-minute timeout) |
| `infra/06_run_glue_job.sh` | Run the Glue job and check partitions and row count |
| `infra/07_athena.sh` | Athena workgroup (scan limit 100 MB), tables, row-count checks |
| `infra/08_athena_views.sh` | KPI reference views |
| `infra/09_tag_coverage.sh` | Check that all cost-relevant resources carry the project tag (read-only) |

Checks after the pipeline:

```bash
python ingestion/compare_kpis.py   # Athena views vs. local validator, exit code 1 on mismatch
bash infra/09_tag_coverage.sh      # exit code 1 if a cost-relevant resource is untagged
```

Optional read-only reports: `infra/10_cost_report.sh` (Cost Explorer,
0.01 USD per request) and `infra/11_inventory.sh` (resource inventory).
Pricing basis: `research/notes/aws-pricing-2026-11.md`.

## Author
Luciano Sulaimon, Business Analyst / Requirements Engineer
[LinkedIn or website]
