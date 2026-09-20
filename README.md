# Wealth Management Analytics QA

## One-Sentence Summary

Built a Snowflake-style financial reporting QA system that combines public SEC adviser data with synthetic wealth-management performance data, injects known reporting errors, detects them with hard rules and statistical anomaly detection, and evaluates QA performance with precision/recall.

## Why This Project Matters

Finance teams need reliable advisor, branch, and firm reporting. If AUM, revenue, account, or fee data is wrong, bad numbers can reach executives, advisors, and business partners before anyone knows there is a data quality issue.

This project models a reporting QA workflow where data quality is measurable instead of only manual or ad hoc. It creates a clean baseline, intentionally seeds known reporting errors, detects issues with multiple rule families, and evaluates the results with precision, recall, false-positive rate, and threshold tradeoffs.

## What Makes This Project Different

The depth story is not "I built a dashboard." The depth story is measured financial reporting QA:

- Seeded known errors into synthetic monthly performance data.
- Preserved a ground-truth answer key for each injected issue.
- Built deterministic hard-rule detectors for impossible or invalid finance records.
- Built statistical anomaly detectors for unusual AUM and revenue patterns.
- Evaluated detection performance with precision, recall, false-positive rate, and F1 score.
- Compared thresholds to show the tradeoff between catching bad numbers and overwhelming reviewers.
- Delivered results through stakeholder-facing Excel and Power BI-ready reporting artifacts.

## Key Results

From the committed [generated QA summary](reports/generated_qa_summary.md):

| Metric | Result |
|---|---:|
| Injected errors | 40 |
| Hard-rule detections | 31 |
| Statistical detections | 2,764 |
| Combined detections | 2,795 |
| Precision | 0.011 |
| Recall | 0.800 |
| False-positive rate | 0.989 |
| F1 score | 0.023 |
| True positives | 32 |
| False positives | 2,763 |
| False negatives | 8 |

Selected operating threshold: `z=3.0_iqr=3.0`.

The key business interpretation is that the current statistical detector configuration catches most seeded issues, but it creates a high reviewer workload. That is intentional for the portfolio story: the project makes the tradeoff visible instead of hiding it.

## Architecture

```text
Public SEC ADV firm data + synthetic private-style performance data
    -> clean baseline validation
    -> KPI SQL views
    -> seeded error injection
    -> hard-rule and statistical detection
    -> precision/recall/FPR evaluation
    -> Excel workbook + Power BI-ready reporting layer
```

The local pipeline can run without Snowflake, while the SQL assets and loader scaffold show how the same design maps to a future Snowflake warehouse.

## Data Boundary and Governance

The project keeps real public data and synthetic private-style data intentionally separate:

- `RAW.SEC_ADV_FIRMS` is reserved for public, real SEC/IAPD adviser firm-level regulatory data.
- `RAW.SYNTHETIC_*` tables are reserved for generated branch, advisor, account, and monthly performance records.

This boundary matters because public firm facts can make the portfolio scenario realistic, while synthetic advisor/account/performance data avoids pretending to use private client data.

## Tech Stack

Python, pandas, Snowflake SQL, pytest, R, Excel export, Power BI-ready CSVs/docs, GitHub Actions.

## Repository Map

- `ingestion/`: SEC ADV ingestion scaffold, Snowflake loader scaffold, and synthetic wealth-management data generator.
- `qa/`: seeded error injection, hard-rule detection, statistical anomaly detection, evaluation metrics, and local QA pipeline.
- `sql/`: Snowflake schema, KPI views, and QA reporting views.
- `reporting/`: Excel export and Power BI-ready export/documentation layer.
- `reports/`: generated QA summary and written portfolio reports.
- `outputs/`: committed small portfolio outputs such as Excel and Power BI-ready CSVs.
- `r/`: exploratory R AUM growth analysis artifact.
- `docs/`: interview story, architecture notes, and Snowflake runbook.
- `tests/`: pytest coverage for ingestion, generation, QA rules, evaluation, reporting exports, and documentation artifacts.

## How To Run

Run the Python test suite:

```bash
python -m pytest
```

Run the local QA pipeline:

```bash
python -m qa.run_local_qa_pipeline
```

Export the stakeholder Excel workbook:

```bash
python -m reporting.export_excel
```

Export Power BI-ready CSVs:

```bash
python -m reporting.export_powerbi_csvs
```

Run the optional R analysis:

```bash
Rscript r/advisor_aum_growth_model.R
```

The R script requires a local R installation and the packages listed in [r/README.md](r/README.md).

## Portfolio Artifacts

- [Generated QA summary](reports/generated_qa_summary.md)
- [Excel stakeholder workbook](outputs/excel/monthly_finance_report.xlsx)
- [Power BI-ready CSV exports](outputs/powerbi/)
- [Power BI handoff guide](reporting/powerbi/README.md)
- [QA evaluation report](reports/qa_evaluation_report.md)
- [R AUM growth model script](r/advisor_aum_growth_model.R)
- [Interview story](docs/interview_story.md)
- [Architecture document](docs/architecture.md)
- [Snowflake runbook](docs/snowflake_runbook.md)

## Interview Talking Points

- Seeded ground truth matters because it turns QA from "rules exist" into measurable precision, recall, and false-positive rate.
- Hard rules catch impossible records, but hard rules alone miss subtle anomalies like unusual AUM growth or revenue spikes.
- Statistical thresholds were compared to show how sensitivity changes reviewer workload and missed issues.
- False positives and false negatives are business tradeoffs: too many false positives waste reviewer time, while false negatives allow bad finance data into reports.
- Real SEC firm data and synthetic private-style data are separated to preserve governance and avoid misrepresenting generated records as real client data.
- Excel and Power BI-ready outputs make the QA layer consumable by finance stakeholders, not only engineers.
- The current results show strong recall but weak precision, which creates a concrete next-step discussion about tuning statistical detectors.

## Current Limitations / Future Work

- No production Snowflake account is connected in CI.
- No finished `.pbix` file is included or claimed.
- SEC ingestion is bounded and scaffolded rather than a full adviser-universe scrape.
- The R script is designed for local execution and may require installing R packages.
- Future work includes running the Snowflake pipeline end to end, ingesting a live SEC file, tuning statistical thresholds, and building a real Power BI dashboard file.
