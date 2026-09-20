# Final Project Audit

Audit date: 2026-09-20

## Test Status

Passed:

```bash
python -m pytest
```

Result observed during final audit: `134 passed`.

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

Passed locally using the installed executable's full path (Rscript is not assumed to be on `PATH`):

```powershell
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" r/advisor_aum_growth_model.R
```

This executed an exploratory analysis of synthetic wealth-management performance data and generated a Markdown model summary plus two small diagnostic plots. It is not a production predictive machine-learning model.

## Artifact Checklist

- [x] `reports/generated_qa_summary.md`
- [x] `reports/qa_evaluation_report.md`
- [x] `reports/r_aum_growth_model_summary.md`
- [x] `reports/sec_adv_ingestion_quality.md` (generated from development sample data)
- [x] `docs/sec_adv_ingestion_guide.md`
- [x] `outputs/r/residuals_vs_fitted.png`
- [x] `outputs/r/aum_growth_by_segment.png`
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
- [x] SEC ADV/IAPD firm data is described as public real firm-level data or as a bounded local-file ingestion path.
- [x] The main portfolio story is measured QA using seeded errors, ground truth, precision, recall, false-positive rate, and threshold tradeoffs.
- [x] Ignored generated QA CSVs may exist locally after command runs, but they are not intended to be committed.

## Generated Data / Git Hygiene

Allowed committed outputs:

- `outputs/excel/monthly_finance_report.xlsx`
- `outputs/powerbi/*.csv`
- `outputs/r/*.png`
- `reports/generated_qa_summary.md`
- `reports/r_aum_growth_model_summary.md`

Ignored generated outputs checked during audit:

- `data/raw/synthetic_corrupted/*.csv`
- `data/raw/sec_adv/*.csv`
- `data/qa/detections/*.csv`
- `data/qa/evaluation/*.csv`
- `data/raw/synthetic/*.csv`
- `data/processed/*.csv`

Private files such as `.env` should remain untracked.

## Known Limitations

- Snowflake schema and loader scaffolds exist, but live Snowflake execution depends on user credentials and a Snowflake account or trial.
- No `.pbix` file is committed.
- The R analysis was executed locally with `C:\Program Files\R\R-4.6.1\bin\Rscript.exe`; Rscript is not claimed to be on `PATH`, and reproducing it elsewhere requires local R plus the documented packages.
- The R model is exploratory analysis on synthetic wealth-management performance data, not production predictive machine learning.
- SEC ADV ingestion supports local official CSV normalization, filtering, sampling, and quality reporting; raw official files are not committed.
- Current QA metrics show high recall but low precision, so statistical detector tuning is a future improvement area.

## Next Optional Improvements

- Run the full SQL stack in a real Snowflake trial with cost controls.
- Tune statistical anomaly thresholds and grouping logic to improve precision.
- Exercise the local ingestion interface with a current official SEC ADV/IAPD export when one is supplied, without committing the raw file.
- Build a real Power BI Desktop `.pbix` from the documented model and CSV exports.
- Add orchestration for repeatable local runs.
