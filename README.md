# Wealth Management Analytics QA

## Project Overview

This project is a Snowflake-based financial reporting QA system for a wealth-management analytics use case. It is designed to show how public regulatory data, synthetic private-style operating data, and a measured QA layer can support trustworthy monthly reporting.

The portfolio story is not simply a dashboard. The centerpiece is a financial reporting QA and anomaly-detection layer that will seed known errors, preserve labeled ground truth, detect anomalies, and evaluate detection quality with precision, recall, and false-positive rate.

## Why This Project Exists

Wealth-management reporting depends on clean adviser, account, asset, and performance data. Small issues such as stale AUM, impossible returns, duplicate accounts, or mismatched adviser relationships can lead to misleading KPI dashboards and poor review decisions.

This project exists to demonstrate an analytics workflow that treats data quality as a measurable product outcome instead of a final manual cleanup step.

## Depth Centerpiece: Financial Reporting QA and Anomaly Detection

Later phases will build a QA layer that:

- Injects known financial reporting errors into synthetic data.
- Stores a labeled ground-truth table for seeded issues.
- Detects anomalies using hard business rules and statistical rules.
- Evaluates precision, recall, false-positive rate, and reviewer tradeoffs.
- Documents threshold choices for finance and analytics stakeholders.

The goal is to make QA performance measurable, explainable, and suitable for recruiter review.

## Real vs Synthetic Data Boundary

`RAW.SEC_ADV_FIRMS` will contain real public SEC/IAPD investment adviser firm data.

`RAW.SYNTHETIC_*` tables will contain generated private-style advisor, account, and monthly performance data.

The real and synthetic layers must stay separated for governance and interpretability. Public adviser facts can support realistic firm context, while synthetic client/account/performance records avoid exposing private financial data. Downstream models and reports should preserve that boundary clearly.

## Planned Architecture

1. Ingest public SEC/IAPD adviser firm data into `RAW.SEC_ADV_FIRMS`.
2. Generate synthetic advisor, account, and monthly performance tables under `RAW.SYNTHETIC_*`.
3. Clean and conform source tables into Snowflake `CLEAN` models.
4. Build analytics and reporting views for portfolio KPIs.
5. Inject seeded data quality issues and store ground-truth labels in the `QA` schema.
6. Detect anomalies with hard rules and statistical thresholds.
7. Evaluate detection performance and document reviewer tradeoffs.
8. Export reporting-ready tables for Excel and Power BI.

## Phase 1 Step 2: SEC ADV Ingestion Interface

The project now includes a local SEC ADV ingestion interface for the future `RAW.SEC_ADV_FIRMS` table. The module supports real-file mode for a staged SEC/IAPD-style CSV and a clearly labeled development fallback sample for offline testing.

This step keeps real SEC adviser firm data structurally separate from synthetic advisor, account, and performance data. Snowflake loading comes later; this phase only normalizes local firm data into a consistent schema.

## Phase 1 Step 3: Snowflake Schema and Loader Scaffold

Snowflake DDL now defines the XS warehouse, `WEALTH_ANALYTICS` database, core schemas, and `RAW.SEC_ADV_FIRMS` table structure. `RAW.SEC_ADV_FIRMS` is reserved for real public SEC/IAPD adviser firm data, while future synthetic data will use separate `RAW.SYNTHETIC_*` tables.

The Python Snowflake loader is credential-safe: it reads local `.env` values, validates required columns, and fails clearly before connecting when credentials are missing. This prepares the warehouse layer before synthetic data generation.

## Phase 2 Step 1: Synthetic Wealth-Management Data

The project now has a reproducible synthetic private-data generator for branches, advisors, client accounts, and monthly performance records. It uses real/public firm-level SEC ADV seed data when available, then writes only clearly labeled synthetic operating data for future `RAW.SYNTHETIC_*` tables.

This keeps synthetic branch, advisor, account, and performance data separate from real SEC ADV firm data. The monthly performance layer is clean baseline data that later phases will intentionally corrupt with seeded errors for QA evaluation.

## Phase 2 Step 2: Synthetic RAW Tables and Integrity Checks

The Snowflake schema now includes RAW table definitions for synthetic branches, advisors, accounts, and monthly performance. These tables are explicitly labeled as synthetic private-style records and remain separate from `RAW.SEC_ADV_FIRMS`.

Local validation checks now protect the clean baseline dataset before any future Snowflake loading or intentional error injection. This matters because the later QA and anomaly-detection phase needs a known-good baseline before seeded corruption can be measured with precision and recall.

## Phase 2 Step 3: Baseline KPI Reporting Views

The project now has clean baseline SQL KPI views for advisor, branch, firm, and executive monthly reporting. These views combine real public firm metadata from `RAW.SEC_ADV_FIRMS` with synthetic private-style performance data from `RAW.SYNTHETIC_*`.

This establishes a known-good reporting foundation before seeded-error QA and anomaly detection. The executive summary intentionally marks QA as `QA_NOT_RUN_YET` because anomaly detection and measured QA evaluation have not been implemented.

## Phase 3 Step 1: Seeded Error Injection

The project now creates a corrupted copy of synthetic monthly performance data and a labeled ground-truth answer key in `QA.GROUND_TRUTH_INJECTED_ERRORS`. The injector records exactly which rows were changed, which field was corrupted, the before/after values, severity, and whether the issue belongs to hard-rule or statistical-rule detection.

This is the start of the depth centerpiece: future phases can measure precision and recall because the project now has known injected errors to detect.

## Phase 3 Step 2: Hard-Rule QA Detection

Hard-rule detection now identifies deterministic financial reporting issues in corrupted synthetic performance data. These rules cover negative AUM and revenue, fee-rate bounds, duplicate account-month rows, revenue on closed accounts, missing parent references, and null key fields.

This is the first detector layer. Statistical anomaly detection comes next, and evaluation against ground truth comes after both detection families exist.

## Phase 3 Step 3: Statistical Anomaly Detection

Statistical detection now identifies unusual AUM growth and revenue patterns using parameterized z-score and IQR rules. This detector family is separate from hard rules: it is designed for subtle changes that can look valid row by row but unusual in context.

Precision and recall evaluation comes next, after both hard-rule and statistical-rule detections are available.

## Phase 3 Step 4: QA Evaluation Metrics

Detection outputs can now be scored against seeded ground truth. The evaluation layer reports precision, recall, false-positive rate, and F1 score, and it records row-level detection-to-ground-truth matches.

Threshold comparison supports the core interview story: choosing a QA operating point based on the tradeoff between catching bad finance data and overwhelming reviewers. This completes the measured QA foundation.

## Phase 3 Step 5: Local QA Pipeline Summary

The local QA pipeline can now run end-to-end without Snowflake. It generates clean synthetic data, injects seeded errors, runs hard-rule and statistical detection, evaluates results, compares thresholds, and writes a portfolio-facing summary report.

Detailed generated CSV outputs are ignored by git, while `reports/generated_qa_summary.md` is committed as the visible proof of the measured QA layer.

## Phase 4 Step 1: Excel Stakeholder Report

The project now exports a stakeholder-ready Excel workbook that combines clean financial KPI reporting with QA evaluation results. This connects the technical QA layer to finance and business partner reporting.

The workbook is written to `outputs/excel/monthly_finance_report.xlsx` and includes executive summary, firm, branch, advisor, QA summary, and QA findings sample sheets.

## Phase 4 Step 2: R AUM Growth Analysis

The project now includes an R exploratory model for account-level monthly AUM growth. The analysis reports model coefficients, confidence intervals, residual diagnostics, and limitations in `reports/r_aum_growth_model_summary.md`.

The model is intentionally framed as exploratory analysis on synthetic project data that supports the seeded-error QA and finance reporting story. It is not production machine learning or a deployable forecasting model.

## Run Local QA Pipeline

```bash
python -m qa.run_local_qa_pipeline
```

Generated raw and detailed CSVs under `data/raw/synthetic_corrupted/`, `data/qa/detections/`, and `data/qa/evaluation/` are ignored. The generated Markdown summary at `reports/generated_qa_summary.md` is committed.

## Export Excel Report

```bash
python -m reporting.export_excel
```

The generated workbook at `outputs/excel/monthly_finance_report.xlsx` is intended to be committed when reasonably small.

## Run R AUM Growth Analysis

```bash
Rscript r/advisor_aum_growth_model.R
```

If the synthetic CSVs are missing, run `python -m ingestion.generate_synthetic` first. The R script writes a Markdown summary under `reports/` and optional diagnostic PNGs under `outputs/r/`.

## Snowflake Setup Notes

- Use an XS warehouse for this portfolio project.
- Set `AUTO_SUSPEND=60` to limit idle warehouse cost.
- Do not start the Snowflake trial until ready to load data.
- Never commit `.env`.

## Planned Tech Stack

- Snowflake for warehouse schemas, views, and reporting layers.
- Python for ingestion, synthetic data generation, QA rules, and evaluation.
- pandas and NumPy for data preparation.
- scikit-learn for evaluation utilities and later modeling support.
- R for an advisor AUM growth modeling component.
- pytest and GitHub Actions for automated validation.
- Power BI and Excel for downstream reporting.

## Repository Structure

```text
wealth-management-analytics-qa/
├── data/raw/                 # Raw SEC/IAPD and synthetic source files
├── ingestion/                # Future SEC fetch and synthetic generation modules
├── qa/                       # Error injection, detection rules, and evaluation
├── sql/                      # Snowflake schema, KPI, and QA view definitions
├── r/                        # Planned R modeling component
├── reporting/                # Excel export and Power BI-ready documentation
├── reports/                  # Written finance and QA reports
├── notebooks/                # Threshold comparison exploration
└── tests/                    # Scaffold and future logic tests
```

## Phase Roadmap

- Phase 1: Create the professional project scaffold and repository foundation.
- Phase 2: Add SEC/IAPD data ingestion and synthetic wealth-management data generation.
- Phase 3: Build Snowflake schemas, clean tables, KPI views, and reporting views.
- Phase 4: Implement error injection, ground-truth labeling, hard rules, and statistical rules.
- Phase 5: Evaluate QA performance with precision, recall, false-positive rate, and threshold tradeoffs.
- Phase 6: Add R modeling, Excel export, Power BI documentation, and final portfolio reports.

## Current Status

Phase 4, Step 2 adds an exploratory R AUM growth analysis artifact. Power BI assets are intentionally not implemented yet.
