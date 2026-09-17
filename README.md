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

Phase 2, Step 2 adds synthetic RAW table definitions and local referential-integrity validation. Error injection, anomaly detection, R modeling, Power BI assets, and Excel exports are intentionally not implemented yet.
