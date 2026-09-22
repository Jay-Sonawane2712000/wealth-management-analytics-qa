# Power BI Reporting Layer

## Purpose

This folder documents the completed Power BI reporting layer for the wealth-management analytics QA project.

## Current Status

The completed report is `outputs/powerbi/wealth_management_analytics_qa.pbix`. It contains three pages: Executive Overview, Advisor Performance, and QA Review.

The current deliverables are:

- The completed PBIX report
- Local CSV exports under `outputs/powerbi/`
- A data dictionary for the exported tables
- DAX measure definitions
- A dashboard layout specification

## Data Sources

Current local prototype source:

- `outputs/powerbi/advisor_kpis.csv`
- `outputs/powerbi/branch_kpis.csv`
- `outputs/powerbi/firm_kpis.csv`
- `outputs/powerbi/qa_metrics.csv`
- `outputs/powerbi/qa_threshold_comparison.csv`

The deployed Snowflake model is an optional source for a separately configured Snowflake-backed version:

- `ANALYTICS.ADVISOR_MONTHLY_KPIS`
- `ANALYTICS.BRANCH_MONTHLY_KPIS`
- `ANALYTICS.FIRM_MONTHLY_KPIS`
- `REPORTING.EXECUTIVE_MONTHLY_SUMMARY`
- `QA.BASELINE_DATA_HEALTH_SUMMARY`
- `QA.HARD_RULE_DETECTION_RESULTS`
- `QA.STATISTICAL_DETECTION_RESULTS`

## Recommended Power BI Import Mode

For the local portfolio prototype, use Import mode with the CSV files in `outputs/powerbi/`.

For a Snowflake-backed version, use Import mode for a small portfolio demo or DirectQuery only when a live warehouse, credentials, permissions, gateway, refresh schedule, and cost controls are intentionally configured.

## Table Relationships

Suggested relationships for the local CSV prototype:

| From Table | From Column | To Table | To Column | Cardinality |
|---|---|---|---|---|
| `advisor_kpis` | `branch_id` | `branch_kpis` | `branch_id` | Many-to-one |
| `advisor_kpis` | `firm_crd_number` | `firm_kpis` | `firm_crd_number` | Many-to-one |
| `branch_kpis` | `firm_crd_number` | `firm_kpis` | `firm_crd_number` | Many-to-one |
| `qa_metrics` | `threshold_label` | `qa_threshold_comparison` | `threshold_label` | Many-to-one |

If Power BI detects ambiguous paths, keep relationships inactive where necessary and use DAX measures over the fact table most relevant to each page.

## Measures

Use `dax_measures.md` as the starting measure catalog. It includes financial measures such as Total AUM, Total Revenue, Net New Assets, AUM Growth Rate, and QA measures such as Precision, Recall, False Positive Rate, and F1 Score.

Column and table names may need adjustment depending on the final import names Power BI assigns.

## Dashboard Pages

The implemented pages are:

1. Executive Overview
2. Advisor Performance
3. QA Review

## Refresh Notes

Generate local CSVs with:

```bash
python -m reporting.export_powerbi_csvs
```

Then open `outputs/powerbi/wealth_management_analytics_qa.pbix` in Power BI Desktop and select **Home > Refresh**. If Power BI cannot find the CSVs because the repository moved, use **File > Options and settings > Data source settings**, select each CSV source, choose **Change Source**, and point it to the matching file under `outputs/powerbi/`. Apply changes, refresh again, and verify all three pages render without visual errors.

## Snowflake Prerequisites

The committed PBIX does not require Snowflake for its normal local CSV refresh. A Snowflake-backed variant requires the schema and data loaders to have completed, all seven views to exist, `ANALYTICS_WH` access through `WEALTH_ANALYTICS_ROLE`, and local credentials in an ignored `.env`. Do not put credentials in the PBIX or repository. Suspend the warehouse after validation.

## Final Validation Workflow

1. Run `python -m pytest`.
2. Run `python -m ingestion.load_project_data_to_snowflake --dry-run` to validate loader inputs without connecting.
3. Run `python -m reporting.export_powerbi_csvs`.
4. Open the PBIX, use **Home > Refresh**, and inspect Executive Overview, Advisor Performance, and QA Review for refresh or visual errors.

## Governance Notes

Real public SEC/IAPD firm data and synthetic private-style operating data remain conceptually separate in the project design. Power BI should preserve that distinction in labels and model documentation.

Do not present the local CSV dashboard as production reporting. A Snowflake-backed deployment requires refresh, permissions, lineage, and cost governance beyond this local portfolio report.
