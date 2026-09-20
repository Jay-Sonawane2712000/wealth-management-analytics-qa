# Power BI Reporting Layer

## Purpose

This folder documents the Power BI-ready reporting layer for the wealth-management analytics QA project. It is meant to help a reviewer or analyst build a manual Power BI prototype from local CSV exports now, and later connect Power BI to Snowflake reporting or analytics views.

## Current Status

This repo currently provides a Power BI-ready reporting layer. A finished `.pbix` file is not included or claimed.

The current deliverables are:

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

Recommended future production source:

- Snowflake analytics/reporting views built from `RAW.SEC_ADV_FIRMS`, `RAW.SYNTHETIC_*`, and QA evaluation tables.

## Recommended Power BI Import Mode

For the local portfolio prototype, use Import mode with the CSV files in `outputs/powerbi/`.

For a future Snowflake-backed version, use Import mode for a small portfolio demo or DirectQuery only if a live warehouse and refresh governance are intentionally configured. This repository does not connect to Snowflake during this step.

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

Use `dashboard_layout.md` for the dashboard wireframe. The intended pages are:

1. Executive Finance Overview
2. Advisor / Branch Performance
3. QA & Anomaly Review

## Refresh Notes

Generate local CSVs with:

```bash
python -m reporting.export_powerbi_csvs
```

Then refresh the imported CSVs in Power BI Desktop. Generated raw synthetic CSVs remain ignored; the curated Power BI exports are intentionally small and portfolio-friendly.

## Manual Build Steps

1. Run `python -m reporting.export_powerbi_csvs`.
2. Open Power BI Desktop.
3. Import the five CSV files from `outputs/powerbi/`.
4. Confirm data types for dates, numeric KPI fields, and percentage fields.
5. Create relationships using the relationship guide above.
6. Add measures from `dax_measures.md`.
7. Build pages using `dashboard_layout.md`.
8. Add a text note that the dashboard is based on synthetic local exports unless connected to Snowflake later.

## Governance Notes

Real public SEC/IAPD firm data and synthetic private-style operating data remain conceptually separate in the project design. Power BI should preserve that distinction in labels and model documentation.

Do not present the local CSV dashboard as production reporting. The recommended future production source is Snowflake reporting/analytics views, with refresh, permissions, and lineage handled outside this local portfolio scaffold.
