# Architecture

## Project Purpose

This project demonstrates a finance reporting QA system for a wealth-management analytics scenario. It is designed to show how reporting pipelines can measure data quality performance instead of relying only on manual checks.

## Data Sources

- Public SEC/IAPD adviser firm data: reserved for `RAW.SEC_ADV_FIRMS`.
- Synthetic private-style data: generated branches, advisors, accounts, and monthly performance records for `RAW.SYNTHETIC_*`.
- Seeded QA data: intentionally corrupted performance rows and ground-truth injected error labels.

## Pipeline Stages

1. Normalize bounded SEC ADV firm data or generate a clearly labeled development sample.
2. Generate synthetic branches, advisors, accounts, and monthly performance data.
3. Validate the clean baseline for referential integrity and financial ranges.
4. Define Snowflake schemas and KPI views for advisor, branch, firm, and executive reporting.
5. Inject known reporting errors and create ground truth.
6. Run hard-rule and statistical anomaly detection.
7. Evaluate detections with precision, recall, false-positive rate, and F1 score.
8. Export stakeholder-facing Excel and a completed Power BI report backed by curated local CSVs.

## Tables and Views

Deployed Snowflake database: `WEALTH_ANALYTICS`.

Core schemas:

- `RAW`: source-shaped SEC and synthetic data.
- `CLEAN`: conformed models.
- `ANALYTICS`: KPI views and analysis-ready tables.
- `REPORTING`: stakeholder-facing reporting views.
- `QA`: seeded errors, detection outputs, and evaluation results.

Important objects:

- `RAW.SEC_ADV_FIRMS`
- `RAW.SYNTHETIC_BRANCHES`
- `RAW.SYNTHETIC_ADVISORS`
- `RAW.SYNTHETIC_ACCOUNTS`
- `RAW.SYNTHETIC_MONTHLY_PERFORMANCE`
- KPI views in `sql/kpi_views.sql`
- QA views in `sql/qa_views.sql`

## QA Evaluation Flow

```text
Clean monthly performance
    -> seeded error injection
    -> corrupted performance + ground truth
    -> hard-rule detection
    -> statistical anomaly detection
    -> combined detections
    -> match detections to ground truth
    -> precision / recall / FPR / F1
    -> threshold comparison
```

Hard rules catch deterministic violations such as negative values, invalid fee rates, duplicate account-month records, and missing parent references. Statistical detectors flag unusual AUM growth and revenue patterns using configurable thresholds.

## Reporting Outputs

- `reports/generated_qa_summary.md`: committed QA summary with actual metrics.
- `outputs/excel/monthly_finance_report.xlsx`: stakeholder workbook.
- `outputs/powerbi/*.csv`: import-ready CSVs for Power BI Desktop.
- `outputs/powerbi/wealth_management_analytics_qa.pbix`: completed three-page Power BI report.
- `reporting/powerbi/`: model guide, data dictionary, DAX measures, and dashboard layout.
- `r/advisor_aum_growth_model.R`: exploratory R analysis artifact.

## Governance Notes

The project deliberately separates real public regulatory data from generated private-style records. Synthetic advisor, account, and performance data should never be presented as real client data. The Power BI and Excel outputs are portfolio artifacts, not production reporting systems.
