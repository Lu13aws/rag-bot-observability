# Requirements: Monitoring for a RAG Assistant

## 1. Context and goal

The monitored system is a fictional RAG (retrieval-augmented generation)
assistant that answers employee questions from an internal knowledge base.
Its setup is inspired by the author's own RAG platform. All data in this
project is synthetic.

Goal: give management, AI engineering and operations one shared, verifiable
view of speed, reliability, answer grounding, user satisfaction and cost,
based on a single KPI catalog (`docs/02-kpi-catalog.md`).

## 2. Stakeholders

| Role | Interest | Reporting need | Default view |
|---|---|---|---|
| Management | Overview, cost, adoption | All KPIs incl. cost and volume, all teams | Week, month |
| AI Engineering | Quality signals, errors | No-source share, feedback, errors per `model_id` and `app_version` | Week |
| Operations | Speed, reliability | p95 latency, error rate | Day |
| Team A / Team B leads | Usage of their own team | KPI overview for their own team only | Week |

## 3. Functional requirements

| ID | Requirement | Priority (MoSCoW) | Acceptance criterion |
|---|---|---|---|
| FR-01 | The dashboard shows all KPIs of the KPI catalog (KPI-01 to KPI-07) for a selected period. | Must | Every KPI value matches its Athena reference query within the tolerance (section 3.1). |
| FR-02 | Users can switch the time grain between day, ISO week and month (Europe/Zurich). | Must | For 3 sample periods per grain, all KPI values match the Athena reference. |
| FR-03 | Users can filter all KPIs by `model_id` and `app_version`. | Must | For 2 sample filter combinations, KPI values match the Athena reference with the same filter. |
| FR-04 | Each KPI is shown as a trend over time. | Must | The trend covers the full data period with one point per period that contains data. |
| FR-05 | KPI values outside their target are highlighted. | Should | Tested with one breaching and one non-breaching period: the highlight appears only for the breaching one. |
| FR-06 | Failed queries can be broken down by `status` and `error_type`. | Could | The sum of the breakdown equals the total number of failed queries. |

### 3.1 Acceptance rule

- Reference: one Athena query per KPI, using the formula from the KPI catalog.
- Tolerance:
  - latency (KPI-01): ±50 ms;
  - ratios and cost (KPI-02 to KPI-06): ±1 % relative;
  - error rate (KPI-02): alternatively ±0.2 percentage points absolute; a
    value passes if it meets at least one of the two limits;
  - query volume (KPI-07): exact match.
- The p95 calculation method is defined in the KPI catalog.

## 4. Non-functional requirements

| ID | Category | Requirement | Acceptance criterion |
|---|---|---|---|
| NFR-01 | Data freshness | The dashboard contains all queries up to the end of the previous day (Europe/Zurich) by 08:00. | A daily QuickSight dataset refresh is scheduled before 08:00, and the refresh history shows a successful run. Note: demo data is static, so freshness is verified through the refresh schedule, not through new data. |
| NFR-02 | Access control (RLS) | Row-level security on `user_group`: Team A sees only `team_a`, Team B sees only `team_b`, Management sees all rows. | Tested with 2-3 reader users (one per role): each user sees only the permitted rows; Team A values match the Athena reference filtered on `team_a`. |
| NFR-03 | Cost | Total AWS cost of the project stays at or below 50 USD per month. No QuickSight Pro users or Q topics (they add an account fee). | AWS Budgets alert configured at 20 USD; month-to-date cost in Cost Explorer ≤ 50 USD; resources deleted after testing. |
| NFR-04 | Traceability | Every dashboard visual refers to a KPI ID; every KPI has one formula in the catalog and one Athena reference query. | Review shows 100 % of visuals mapped to a KPI ID. |
| NFR-05 | Data protection | Only synthetic data; no personal data and no secrets in the repository. | The generator uses no real names; the repository is checked for credentials before each commit. |

## 5. Data sources and assumptions

Source: synthetic query logs from a Python generator (planned).

### 5.1 Data model (design, not yet implemented)

Table `rag_query_log`: one row per query. Parquet/Snappy, Hive-partitioned
by `dt`.

| Field | Type | Description | Used by |
|---|---|---|---|
| `query_id` | string | Unique query ID (UUID), primary key | KPI-07, all denominators |
| `event_ts` | timestamp (UTC) | Time the query was received | All (time axis) |
| `dt` | string | Partition, local date in Europe/Zurich (`YYYY-MM-DD`) | All (partition pruning) |
| `status` | string | `success`, `error` or `timeout` | KPI-01, KPI-02, KPI-03 |
| `error_type` | string, nullable | Error category, only if `status` is not `success` | FR-06 |
| `latency_ms` | int | Total response time | KPI-01 |
| `sources_count` | int | Number of retrieved sources used in the answer | KPI-03 |
| `tokens_in` | int | Prompt tokens | KPI-06 |
| `tokens_out` | int | Completion tokens | KPI-06 |
| `feedback` | smallint, nullable | `1` positive, `-1` negative, `null` not rated | KPI-04, KPI-05 |
| `model_id` | string | LLM used (`model-small` or `model-large`) | KPI-06, FR-03 |
| `app_version` | string | Assistant release | FR-03 |
| `user_group` | string | `team_a` or `team_b` | NFR-02 (RLS) |

Table `model_pricing`: cost is calculated from this table, not stored in the
log. **Models and prices are fictional** and do not represent any real
provider.

| `model_id` | `price_in_per_1k` (USD) | `price_out_per_1k` (USD) | `valid_from` |
|---|---|---|---|
| `model-small` | 0.002 | 0.006 | 2026-01-01 |
| `model-large` | 0.006 | 0.018 | 2026-01-01 |

At about 2,000 input and 300 output tokens, a query costs about 0.006 USD
(`model-small`) or 0.017 USD (`model-large`).

### 5.2 Assumptions

- A-1: Feedback is stored in the same log record as the query. This is a
  simplification; in a real system feedback arrives later as a separate event.
- A-2: A query gets `status = 'timeout'` if it exceeds 30,000 ms.
- A-3: `event_ts` is stored in UTC; days, weeks, months and the partition `dt`
  use Europe/Zurich.
- A-4: The synthetic data covers 90 days.

## 6. Out of scope

- Answer quality evaluation (faithfulness, relevance): requires an evaluation
  pipeline; only proxy signals (sources, feedback) are covered.
- Real-time alerting: the pipeline is a daily batch.
- Real user data: public repository, synthetic data only.
- Availability / uptime KPI: logs only contain received queries, so outages
  without incoming queries are invisible. This would need an external health
  check.
- Non-token costs (embeddings, hosting, AWS) in KPI-06.

## 7. Open points

- AWS prices (S3, Glue, Athena, QuickSight incl. reader users for the RLS
  test) are verified before the pipeline is built.
