# Final Project Audit

Audit date: 2026-09-20

## Test Status

Passed:

```bash
python -m pytest
```

Result observed during final audit: `125 passed`.

## Pipeline Command Status

Passed:

```bash
python -m qa.run_local_qa_pipeline
```

Observed summary:

- Injected errors: 40
- Hard-rule detections: 31
- Statistical detections: 2,764
- Overall precision: 0.011
- Overall recall: 0.800
- False-positive rate: 0.989
- Selected threshold: `z=3.0_iqr=3.0`

Passed:

```bash
python -m reporting.export_excel
```

Output verified:

- `outputs/excel/monthly_finance_report.xlsx`

Passed:

```bash
python -m reporting.export_powerbi_csvs
```

Outputs verified:

- `outputs/powerbi/advisor_kpis.csv`
- `outputs/powerbi/branch_kpis.csv`
- `outputs/powerbi/firm_kpis.csv`
- `outputs/powerbi/qa_metrics.csv`
- `outputs/powerbi/qa_threshold_comparison.csv`

R was not required for final audit because the README documents that it requires a local R installation and packages.

## Artifact Checklist

- [x] `reports/generated_qa_summary.md`
- [x] `reports/qa_evaluation_report.md`
- [x] `outputs/excel/monthly_finance_report.xlsx`
- [x] `outputs/powerbi/advisor_kpis.csv`
- [x] `outputs/powerbi/branch_kpis.csv`
- [x] `outputs/powerbi/firm_kpis.csv`
- [x] `outputs/powerbi/qa_metrics.csv`
- [x] `outputs/powerbi/qa_threshold_comparison.csv`
- [x] `reporting/powerbi/README.md`
- [x] `reporting/powerbi/data_dictionary.md`
- [x] `reporting/powerbi/dax_measures.md`
- [x] `reporting/powerbi/dashboard_layout.md`
- [x] `docs/interview_story.md`
- [x] `docs/architecture.md`
- [x] `docs/snowflake_runbook.md`

## Claim Audit Checklist

- [x] The repository does not claim that a finished Power BI `.pbix` file is included.
- [x] The repository does not claim live Snowflake execution in CI or in this local audit.
- [x] Advisor, account, branch, and monthly performance data are described as synthetic private-style data.
- [x] SEC ADV/IAPD firm data is described as public real firm-level data or as a bounded/scaffolded ingestion path.
- [x] The main portfolio story is measured QA using seeded errors, ground truth, precision, recall, false-positive rate, and threshold tradeoffs.
- [x] Ignored generated QA CSVs may exist locally after command runs, but they are not intended to be committed.

## Generated Data / Git Hygiene

Allowed committed outputs:

- `outputs/excel/monthly_finance_report.xlsx`
- `outputs/powerbi/*.csv`
- `reports/generated_qa_summary.md`

Ignored generated outputs checked during audit:

- `data/raw/synthetic_corrupted/*.csv`
- `data/qa/detections/*.csv`
- `data/qa/evaluation/*.csv`
- `data/raw/synthetic/*.csv`
- `data/processed/*.csv`

Private files such as `.env` should remain untracked.

## Known Limitations

- Snowflake schema and loader scaffolds exist, but live Snowflake execution depends on user credentials and a Snowflake account or trial.
- No `.pbix` file is committed.
- The R script requires local R and package installation.
- SEC ADV ingestion is bounded/scaffolded for portfolio use, not a full production-scale adviser scrape.
- Current QA metrics show high recall but low precision, so statistical detector tuning is a future improvement area.

## Next Optional Improvements

- Run the full SQL stack in a real Snowflake trial with cost controls.
- Tune statistical anomaly thresholds and grouping logic to improve precision.
- Ingest an official SEC ADV/IAPD export file through the bounded ingestion interface.
- Build a real Power BI Desktop `.pbix` from the documented model and CSV exports.
- Add orchestration for repeatable local runs.
