# AWS pricing check (November 2026)

- **Retrieved:** 2026-11-24
- **Region:** EU (Frankfurt) `eu-central-1`
- **Purpose:** check that the project fits the cost limit of 50 USD per month
  (NFR-03) before any AWS resource is created.
- **Method:** official AWS pricing pages, plus the AWS Price List API for
  region-specific values (the pricing pages render regional tables with
  JavaScript, so their text often shows no region). Prices change; re-check
  before relying on them.

## Prices

### Amazon S3

Source: AWS Price List API `AmazonS3/eu-central-1` (publication date
2026-11-21), [S3 pricing](https://aws.amazon.com/s3/pricing/).

| Item | Price (eu-central-1) |
|---|---|
| S3 Standard storage, first 50 TB | 0.0245 USD per GB-month |
| PUT, COPY, POST, LIST requests | 0.0054 USD per 1,000 |
| GET and all other requests | 0.0043 USD per 10,000 |
| Free tier | New accounts since 2025-07-15: up to 200 USD credits, usable within 12 months of account creation (pricing page) |

### AWS Glue

Source: AWS Price List API `AWSGlue/eu-central-1` (publication date
2026-11-22), [Glue pricing](https://aws.amazon.com/glue/pricing/).

| Item | Price / rule |
|---|---|
| ETL job (Spark) | 0.44 USD per DPU-hour |
| ETL job, Glue 6.0+ | 0.308 USD per DPU-hour |
| Flex execution | 0.29 USD per DPU-hour (Glue 6.0+: 0.203 USD) |
| Billing | Per second, 1-minute minimum (Glue 2.0 and later) |
| DPUs per Spark job | Default 10, minimum 2; 1 DPU = 4 vCPU and 16 GB memory |
| Crawler | 0.44 USD per DPU-hour; minimum duration not stated in the page text |
| Data Catalog | First 1 million objects and first 1 million requests per month free; then 1 USD per 100,000 objects or per 1 million requests |

### Amazon Athena

Source: AWS Price List API `AmazonAthena/eu-central-1` (publication date
2026-11-20), [Athena pricing](https://aws.amazon.com/athena/pricing/).

| Item | Price / rule |
|---|---|
| SQL queries | 5.00 USD per TB scanned |
| Minimum per query | 10 MB, rounded up to the next MB. The page states this only for federated queries. |
| Free tier | Not stated on the page |

### Amazon Quick Sight

Sources: AWS Price List API `AmazonQuickSight/eu-central-1` (publication date
2026-10-31), [Quick Sight pricing](https://aws.amazon.com/quick/quicksight/pricing/),
[Quick Sight FAQs](https://aws.amazon.com/quick/quicksight/faqs/),
[Quick pricing](https://aws.amazon.com/quick/pricing/).

| Item | Value | Source |
|---|---|---|
| Author | 24 USD per user/month | Pricing page (no eu-central-1 entry in the price list) |
| Reader | 3 USD per user/month | Pricing page, price list |
| Author Pro / Reader Pro | 40 / 20 USD per user/month | Pricing page, price list |
| SPICE | 10 GB included per Author; extra 0.38 USD per GB-month | Pricing page, price list |
| Infrastructure fee | 250 USD per month per account | Pricing page, price list ("Q fee") |
| Free trial | 30 days, up to 25 users, all features; subscription and infrastructure fee waived; no credit card required | FAQ, Quick pricing page |
| After the trial | "customers with an AWS account will start being billed for an Enterprise plan" | Quick pricing page |
| Row-level security, Readers | Enterprise Edition only; Enterprise cannot be downgraded to Standard | FAQ |
| Standard Edition | 12 USD per user/month; no RLS, no Readers | Pricing page |

**Conflict: when does the 250 USD infrastructure fee apply?**

| Page | Trigger as stated |
|---|---|
| Quick Sight pricing | Account has a Pro user, Q&A via topics or dashboard Q&A ("any of the following"; another footnote on the same page uses "and") |
| Quick Sight FAQ | Billed each month there are Pro users or topics in the account |
| Quick pricing | Flat "+$250 infrastructure fee per account" for the Essentials, Professional and Enterprise organization plans |

The pages do not state clearly whether a BI-only account without Pro users
and without topics avoids the fee after the trial.

### AWS Budgets

Source: [AWS Budgets pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/),
[Creating a cost budget](https://docs.aws.amazon.com/cost-management/latest/userguide/create-cost-budget.html).

- "You can monitor and receive notifications on your budgets free of charge."
- First two action-enabled budgets free; then 0.10 USD per day each.
- Budget reports: 0.01 USD per report delivered.
- Email recipients must verify their address; Cost Explorer is enabled with
  the first budget and its graph can take up to 24 hours to appear.

## Cost estimate for this project

| Service | Assumption | Estimated cost |
|---|---|---|
| S3 | About 10 MB of data, a few thousand requests | < 0.05 USD |
| Glue ETL | 2 DPUs, about 3 minutes per run, about 10 test runs | about 0.30-0.45 USD |
| Glue crawler | Not used (table defined with DDL instead) | 0 USD |
| Data Catalog | Far below the free tier | 0 USD |
| Athena | Even at 10 MB per query, 1,000 queries | about 0.05 USD |
| Quick Sight in trial | 1 Author, up to 3 Readers | 0 USD |
| **Total with trial** | | **< 1 USD** |
| Quick Sight without trial | 24 + 3 × 3 USD | about 34 USD in total |
| Worst case | Infrastructure fee applies | about 284 USD, above the limit |

## Decisions

- **Region:** `eu-central-1` (Frankfurt), the closest region to the
  Europe/Zurich reporting time zone that offers all four services.
- **Quick Sight only within the 30-day trial:** prepare data, Athena views and
  the dashboard design before subscribing; cancel before day 30. The
  cancellation date is set as a calendar reminder on the day the trial starts.
- **No Pro users, no topics, no Q&A** in Quick Sight.
- **Glue jobs with 2 DPUs** (not the default 10) and Glue 6.0 if available.
- **AWS Budgets alert** before the first resource: 50 USD monthly budget,
  alerts at 20 USD and 40 USD actual and 100 % forecasted.

## Rejected approaches

- **Quick Sight Standard Edition** (12 USD/month): no row-level security and
  no Readers, so NFR-02 cannot be met.
- **Quick Sight beyond the trial:** the infrastructure fee is unclear and
  could exceed the budget several times over.
- **Glue crawler:** costs DPU time for a schema that is already known; an
  Athena DDL statement defines the table for free.

## Open points

- Whether the AWS account is eligible for the 200 USD free tier credits
  (account created after 2025-07-15).
- Exact infrastructure-fee trigger after the Quick Sight trial (see conflict
  above). Avoided by the trial-only decision.
