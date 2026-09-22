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
- Delivered results through stakeholder-facing Excel and a completed three-page Power BI report.

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

## Live Snowflake Deployment

The workflow was executed successfully in a Snowflake Standard trial on Azure West US 2 using a custom least-privilege role and an X-Small warehouse. It loaded 30 public SEC ADV firm rows plus 310,275 synthetic/QA rows across nine tables, deployed and verified seven analytics/reporting/QA views, and suspended the warehouse after execution. Credentials remained local and live Snowflake is excluded from CI because of secrets, trial availability, and cost.

See the [live Snowflake execution report](reports/snowflake_live_execution.md) for verified table counts, view results, baseline health checks, and detection interpretation.

## Architecture

```text
Public SEC ADV firm data + synthetic private-style performance data
    -> clean baseline validation
    -> KPI SQL views
    -> seeded error injection
    -> hard-rule and statistical detection
    -> precision/recall/FPR evaluation
    -> Excel workbook + Power BI report
```

The local pipeline can run without Snowflake. The SEC ADV workflow can normalize, filter, sample, and quality-profile a user-supplied official/local CSV, while the SQL assets and loaders implement the deployed Snowflake version. It does not scrape the web or claim a completed full-universe production ingestion.

## Data Boundary and Governance

The project keeps real public data and synthetic private-style data intentionally separate:

- `RAW.SEC_ADV_FIRMS` is reserved for public, real SEC/IAPD adviser firm-level regulatory data.
- `RAW.SYNTHETIC_*` tables are reserved for generated branch, advisor, account, and monthly performance records.

This boundary matters because public firm facts can make the portfolio scenario realistic, while synthetic advisor/account/performance data avoids pretending to use private client data.

## Tech Stack

Python, pandas, Snowflake SQL, pytest, R, Excel export, Power BI Desktop, GitHub Actions.

## Repository Map

- `ingestion/`: offline SEC ADV local-file normalization and quality profiling, Snowflake loader scaffold, and synthetic wealth-management data generator.
- `qa/`: seeded error injection, hard-rule detection, statistical anomaly detection, evaluation metrics, and local QA pipeline.
- `sql/`: Snowflake schema, KPI views, and QA reporting views.
- `reporting/`: Excel export and Power BI export/documentation layer.
- `reports/`: generated QA summary and written portfolio reports.
- `outputs/`: small portfolio outputs such as Excel, Power BI CSVs, R plots, and the completed PBIX report.
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

Normalize a user-supplied official/local SEC ADV CSV:

```bash
python -m ingestion.fetch_sec_adv --input data/raw/sec_adv/my_file.csv --state AZ --max-rows 300
```

Or exercise the same interface with clearly labeled development sample data:

```bash
python -m ingestion.fetch_sec_adv --use-sample --max-rows 30
```

See the [SEC ADV local ingestion guide](docs/sec_adv_ingestion_guide.md) for input handling, quality reporting, and governance details.

Export the stakeholder Excel workbook:

```bash
python -m reporting.export_excel
```

Export Power BI-ready CSVs:

```bash
python -m reporting.export_powerbi_csvs
```

Run the optional R analysis locally on Windows with the installed R executable (Rscript is not assumed to be on `PATH`):

```powershell
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" r/advisor_aum_growth_model.R
```

The exploratory analysis has been executed locally with that full Rscript path against synthetic wealth-management performance data. It generated the committed [R AUM growth model summary](reports/r_aum_growth_model_summary.md) and small diagnostic plots under [`outputs/r/`](outputs/r/). The script requires the packages listed in [r/README.md](r/README.md).

## Portfolio Artifacts

- [Generated QA summary](reports/generated_qa_summary.md)
- [Excel stakeholder workbook](outputs/excel/monthly_finance_report.xlsx)
- [Completed Power BI report](outputs/powerbi/wealth_management_analytics_qa.pbix)
- [Power BI CSV exports](outputs/powerbi/)
- [Power BI handoff guide](reporting/powerbi/README.md)
- [QA evaluation report](reports/qa_evaluation_report.md)
- [Live Snowflake execution report](reports/snowflake_live_execution.md)
- [SEC ADV ingestion quality report](reports/sec_adv_ingestion_quality.md)
- [SEC ADV local ingestion guide](docs/sec_adv_ingestion_guide.md)
- [R AUM growth model script](r/advisor_aum_growth_model.R)
- [Generated R AUM growth model summary](reports/r_aum_growth_model_summary.md)
- [R diagnostic plots](outputs/r/)
- [Interview story](docs/interview_story.md)
- [Architecture document](docs/architecture.md)
- [Snowflake runbook](docs/snowflake_runbook.md)

## Interview Talking Points

- Seeded ground truth matters because it turns QA from "rules exist" into measurable precision, recall, and false-positive rate.
- Hard rules catch impossible records, but hard rules alone miss subtle anomalies like unusual AUM growth or revenue spikes.
- Statistical thresholds were compared to show how sensitivity changes reviewer workload and missed issues.
- False positives and false negatives are business tradeoffs: too many false positives waste reviewer time, while false negatives allow bad finance data into reports.
- Real SEC firm data and synthetic private-style data are separated to preserve governance and avoid misrepresenting generated records as real client data.
- Excel and the completed Power BI report make the QA layer consumable by finance stakeholders, not only engineers.
- The current results show strong recall but weak precision, which creates a concrete next-step discussion about tuning statistical detectors.

## Current Limitations / Future Work

- No production Snowflake account is connected in CI.
- The PBIX uses local Import-mode CSV sources; a Snowflake-backed refresh remains a separately governed deployment choice.
- SEC ADV ingestion supports user-supplied official/local CSV normalization, filtering, sampling, and quality reporting; it performs no scraping, and raw official files are not committed.
- The R analysis is exploratory, uses synthetic wealth-management performance data, and is not production predictive machine learning.
- Future work includes exercising local ingestion with a current official SEC/IAPD export supplied by the user, tuning statistical thresholds, and optionally configuring a governed Snowflake-backed Power BI refresh.
