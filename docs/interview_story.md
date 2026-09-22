# Interview Story

## 30-Second Explanation

I built a wealth-management reporting QA project that treats data quality as a measurable analytics outcome. It combines public SEC adviser firm context with synthetic advisor, account, and monthly performance data, injects known reporting errors, detects them with hard rules and statistical anomaly detection, and evaluates the detectors with precision, recall, and false-positive rate. The result is a portfolio project that shows finance reporting, QA measurement, and stakeholder-ready outputs in Excel and a completed Power BI report.

## 2-Minute Explanation

The project starts with a clear data boundary: real public SEC/IAPD adviser firm data is reserved for `RAW.SEC_ADV_FIRMS`, while private-style advisor, account, and performance data is generated synthetically under `RAW.SYNTHETIC_*`. That keeps the governance story honest.

From there, the system generates a clean baseline dataset, validates it, and builds KPI views for advisor, branch, firm, and executive reporting. The depth layer is the QA workflow: I intentionally inject known reporting errors and preserve a ground-truth answer key. Then I run hard-rule checks for deterministic problems like negative AUM, invalid fees, duplicate account-month rows, and revenue on closed accounts. I also run statistical anomaly checks for unusual AUM growth and revenue patterns.

The important part is evaluation. The project scores detections against ground truth and reports precision, recall, false-positive rate, and F1 score. It also compares thresholds so the conversation becomes practical: how many bad records do we catch, and how much review workload do we create?

Finally, I exported the outputs into a stakeholder Excel workbook and a three-page Power BI report backed by curated local CSVs.

## STAR Story

Situation: Wealth-management reporting depends on accurate AUM, revenue, fee, account, advisor, and branch data. Manual QA can miss issues or fail to quantify whether controls are actually working.

Task: Build a portfolio project that demonstrates not just reporting, but measurable financial reporting QA with an honest data-governance story.

Action: I created synthetic private-style wealth-management data, added public SEC adviser firm context, injected known reporting errors, built hard-rule and statistical detectors, and evaluated detections against a ground-truth answer key. I then surfaced the results in generated reports, Excel, and a completed Power BI report.

Result: The committed QA summary shows 40 injected errors, 2,795 combined detections, 0.800 recall, 0.011 precision, and 0.989 false-positive rate. The numbers expose the tradeoff clearly: the current detector setup catches most seeded issues but creates too much reviewer workload, which points naturally to threshold tuning and detector refinement.

## Technical Deep Dive

- Ingestion separates public SEC ADV firm records from synthetic private-style performance records.
- The synthetic generator creates branches, advisors, accounts, and monthly performance data.
- Baseline validation checks referential integrity and financial ranges before any corruption.
- Error injection creates a corrupted performance dataset and a labeled ground-truth table.
- Hard-rule detection catches deterministic data quality issues.
- Statistical detection uses z-score and IQR-style thresholds for unusual AUM and revenue movements.
- Evaluation prevents duplicate detections from inflating true positives.
- Threshold comparison makes reviewer workload visible through precision, recall, false-positive rate, and F1 score.

## Business Tradeoff Explanation

The project is intentionally honest about QA tradeoffs. A detector with high recall may catch more bad finance records, but if precision is low, reviewers spend time chasing false positives. A conservative detector may reduce reviewer workload but miss real issues. That tension is exactly why precision, recall, false-positive rate, and threshold comparison belong in a finance QA workflow.

## What I Would Improve Next

- Tune statistical thresholds and add better grouping logic to improve precision.
- Add model features that distinguish market-driven movement from data quality anomalies.
- Extend the completed Snowflake deployment with repeatable orchestration and monitoring.
- Exercise the strengthened local ingestion workflow with a current official SEC ADV/IAPD export supplied by the user, while keeping the raw file untracked.
- Optionally configure a governed Snowflake-backed Power BI refresh.
- Add orchestration and scheduled refresh around the local pipeline.

## Resume Bullet Options

### A. Data Analyst Version

- Built a wealth-management reporting QA project with advisor, branch, firm, and executive KPI outputs, including Excel and a three-page Power BI report.
- Evaluated seeded financial reporting errors with precision, recall, false-positive rate, and threshold tradeoff analysis to quantify data quality controls.
- Created stakeholder-ready documentation and reporting outputs that translate technical QA results into finance review workflows.

### B. Data Engineer Version

- Designed a Snowflake-style analytics pipeline separating public SEC adviser firm data from synthetic private-style advisor/account/performance tables.
- Built local ingestion, synthetic generation, validation, seeded-error injection, detection, and evaluation modules with pytest coverage.
- Deployed Snowflake SQL schemas/views and credential-safe bulk loaders while keeping generated raw data out of version control.

### C. Quant / Analytics Version

- Developed hard-rule and statistical anomaly detectors for synthetic wealth-management performance data and scored them against labeled ground truth.
- Compared z-score and IQR threshold configurations using precision, recall, false-positive rate, and F1 score to frame reviewer workload tradeoffs.
- Added an exploratory R regression artifact for account-level AUM growth analysis with coefficients, confidence intervals, diagnostics, and limitations.
