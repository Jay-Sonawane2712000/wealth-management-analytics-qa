# Snowflake Live Execution Report

Execution date: 2026-09-20

## Environment and Governance

The portfolio workflow was executed successfully in a Snowflake Standard trial hosted on Azure West US 2. Execution used the custom `WEALTH_ANALYTICS_ROLE` and the X-Small `ANALYTICS_WH` warehouse.

Credentials remained only in the local, git-ignored `.env` file and were never committed. This report intentionally excludes organization names, account locators, login identifiers, passwords, and other account-specific connection details.

Live Snowflake execution remains intentionally excluded from CI because CI must not depend on local secrets, temporary trial availability, or usage that can incur warehouse cost. Offline validation and mocked connector tests provide CI-safe coverage for the deployment logic.

## Loaded Data

The public firm layer contains 30 SEC ADV firm rows. These public firm-level records remain separate from the synthetic private-style operating data.

The bulk project-data workflow loaded and verified all nine synthetic and QA destinations:

| Destination table | Loaded and verified rows |
| --- | ---: |
| `RAW.SYNTHETIC_BRANCHES` | 102 |
| `RAW.SYNTHETIC_ADVISORS` | 594 |
| `RAW.SYNTHETIC_ACCOUNTS` | 22,481 |
| `RAW.SYNTHETIC_MONTHLY_PERFORMANCE` | 269,772 |
| `RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED` | 11,589 |
| `QA.GROUND_TRUTH_INJECTED_ERRORS` | 40 |
| `QA.DETECTION_RESULTS` | 2,795 |
| `QA.EVALUATION_METRICS` | 99 |
| `QA.DETECTION_GROUND_TRUTH_MATCHES` | 2,803 |
| **Total** | **310,275** |

The loader validated source schemas and types before connecting, refused nonempty targets to prevent duplicate loads, used `write_pandas` for bulk transfer, and verified each destination count after loading.

## Deployed and Verified Views

The reusable deployment module executed four statements from `sql/kpi_views.sql` followed by three statements from `sql/qa_views.sql`. All seven expected views were confirmed through `INFORMATION_SCHEMA.VIEWS`.

| View | Verified rows |
| --- | ---: |
| `ANALYTICS.ADVISOR_MONTHLY_KPIS` | 7,128 |
| `ANALYTICS.BRANCH_MONTHLY_KPIS` | 1,224 |
| `ANALYTICS.FIRM_MONTHLY_KPIS` | 360 |
| `REPORTING.EXECUTIVE_MONTHLY_SUMMARY` | 12 |
| `QA.BASELINE_DATA_HEALTH_SUMMARY` | 7 health checks |
| `QA.HARD_RULE_DETECTION_RESULTS` | 31 |
| `QA.STATISTICAL_DETECTION_RESULTS` | 466 |

## Baseline Data Health

The clean synthetic baseline returned PASS for all three issue checks:

| Check | Issue count | Status |
| --- | ---: | --- |
| Invalid fee rate count | 0 | PASS |
| Negative ending AUM count | 0 | PASS |
| Negative revenue count | 0 | PASS |

The same health view reported informational source counts of 102 branches, 594 advisors, 22,481 accounts, and 269,772 monthly performance rows.

## Detection Interpretation

The warehouse views produced 31 SQL hard-rule detections and 466 SQL statistical detections.

The SQL statistical view and the local Python statistical detector use different implementations and granularity. The SQL view aggregates monthly account metrics and applies its warehouse-side windowed z-score logic, while the local Python workflow evaluates its configured row-level/grouped z-score and IQR rules. Therefore, the 466 SQL detections must not be claimed to equal or reproduce the 2,764 local Python detections. They are separate, useful validation outputs from different detection designs.

## Cost Control and Completion

`ANALYTICS_WH` was suspended after the bulk load and again after view deployment verification. All loader and deployment cursors and connections were closed.
