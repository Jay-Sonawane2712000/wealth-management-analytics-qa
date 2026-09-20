# AI Workflow Log

## Objective

## Prompts and Decisions

### 2026-09-17 - Phase 1 Step 2 SEC ADV Ingestion

We added bounded SEC ADV firm ingestion instead of trying to ingest the full adviser universe at this stage. The module is designed for a portfolio-friendly sample workflow that can normalize a local SEC/IAPD-style CSV into the future `RAW.SEC_ADV_FIRMS` structure.

We also added a development fallback sample so tests and repository structure can work before downloading or staging official files. The fallback is explicitly labeled with `source_type = "development_sample"` to avoid misrepresenting generated sample rows as real regulatory data.

Real SEC adviser firm data remains separated from future synthetic advisor, account, and performance data for governance and interpretability.

### 2026-09-17 - Phase 1 Step 3 Snowflake Schema and Loader

We scaffolded Snowflake loading after local SEC ADV normalization so the project has a clean handoff from local CSV preparation to the future warehouse table. This keeps the first warehouse step narrow: `RAW.SEC_ADV_FIRMS` only.

Tests should not depend on a live Snowflake account because portfolio reviewers and local development environments may not have credentials configured. The loader validates environment variables and data shape first, then fails with a clear message before any connection attempt when credentials are missing.

Real public SEC/IAPD adviser firm data remains assigned to `RAW.SEC_ADV_FIRMS`. Future generated advisor, account, and performance data will use separate `RAW.SYNTHETIC_*` tables so public regulatory data and synthetic private-style data are not blurred.

### 2026-09-17 - Phase 2 Step 1 Synthetic Wealth-Management Generator

Advisor, account, and monthly performance data must be synthetic because those records represent private-style operating data that should not come from public SEC/IAPD files or expose real client relationships.

The generator uses real public firm seed data when available so the synthetic layer can inherit realistic firm context while still keeping branch, advisor, account, and performance records clearly labeled as `source_type = "synthetic"`.

Clean baseline data comes before injected-error QA because later precision and recall evaluation needs a known-good starting point. Errors should be added intentionally in a controlled QA phase, not mixed into the first synthetic data generator.

### 2026-09-17 - Phase 2 Step 2 Synthetic Integrity Validation

We added local referential-integrity validation before loading or corrupting synthetic data so the project can prove the baseline branch, advisor, account, and monthly performance layer is internally consistent.

Clean baseline validation is separate from later anomaly detection. These checks guard expected parent-child links and financial ranges; later QA phases will intentionally seed errors and evaluate whether anomaly rules detect them.

Synthetic data remains clearly labeled in `RAW.SYNTHETIC_*` tables and stays separate from `RAW.SEC_ADV_FIRMS`, which is reserved for real public SEC/IAPD adviser firm data.

### 2026-09-17 - Phase 2 Step 3 Baseline KPI Reporting Views

We built KPI views before anomaly injection so the project has a known-good reporting layer for advisor, branch, firm, and executive summaries. Later seeded-error QA can then compare corrupted data against a clean reporting foundation.

`QA_NOT_RUN_YET` is used honestly in the executive summary instead of pretending QA is complete. The project has baseline validation and health checks, but full injected-error anomaly detection and precision/recall evaluation come later.

The SQL is tested offline by checking structure, required view names, source table references, and safe-division patterns because Snowflake execution is not required yet.

### 2026-09-17 - Phase 3 Step 1 Seeded Error Injection

Seeded-error injection comes before detection because the project needs a controlled set of known bad records before it can honestly evaluate whether QA rules find them.

The ground-truth answer key is necessary for precision and recall: every injected issue records the corrupted row, field, original value, corrupted value, severity, and detection family.

Both obvious deterministic errors and subtle statistical anomalies are included so later QA can test simple business-rule checks as well as threshold-based anomaly detection.

### 2026-09-18 - Phase 3 Step 2 Hard-Rule Detection

Hard rules are separated from statistical anomaly detection because they answer a different question: whether deterministic business constraints were violated, not whether a value is unusual relative to a pattern.

These checks are necessary but not enough for the project depth story. Negative values, invalid fee rates, duplicate account-month records, missing references, and null keys should be caught reliably, while subtler AUM and revenue anomalies will need statistical rules later.

Evaluation is delayed until after both detection families exist so precision and recall can be measured across the full intended QA surface instead of only the obvious deterministic cases.

### 2026-09-18 - Phase 3 Step 3 Statistical Detection

Statistical detection is needed in addition to hard rules because some seeded problems are not impossible values; they are unusual movements, such as extreme AUM jumps or revenue spikes.

Thresholds are parameterized so later phases can tune reviewer workload versus missed anomalies instead of hardcoding one arbitrary sensitivity level.

Small groups are skipped to avoid unreliable statistics. A z-score or IQR threshold is only meaningful when there is enough history to compare against.

Evaluation is still delayed until the next phase because both hard-rule and statistical-rule detections should be scored together against the seeded-error ground truth.

### 2026-09-18 - Phase 3 Step 4 QA Evaluation Metrics

Evaluation comes after both detector families because the portfolio story needs to score the complete QA surface: deterministic hard rules plus statistical anomaly checks.

Exact rule matching is used for hard rules because those seeded errors map directly to deterministic checks. Statistical anomalies can match at the detection-family level by `performance_id` because z-score and IQR methods may both detect the same injected AUM or revenue anomaly.

Duplicate detections must not inflate true positives. One seeded ground-truth error can only be counted once; extra flags become false positives.

Threshold comparison is the main depth story because it shows the tradeoff between catching more bad finance data and creating extra reviewer workload.

### 2026-09-18 - Phase 3 Step 5 Local QA Summary

We generated a committed summary report while keeping detailed generated CSVs ignored because the portfolio needs a readable proof artifact, not large generated data files in git.

The default operating threshold is currently `z=2.5` and `iqr=2.0` because it is a moderate starting point between highly sensitive review settings and overly conservative settings.

This threshold can be revised after reviewing actual precision, recall, false-positive rate, and reviewer workload tradeoffs from the generated threshold comparison.

### 2026-09-18 - Phase 4 Step 1 Excel Stakeholder Report

Excel export matters for corporate finance analytics roles because stakeholders often consume KPI summaries, controls, and QA outcomes in workbook form before a dashboard exists.

The QA summary is included as a first-class sheet instead of hidden technical output because data quality is part of the business story, not just an engineering detail.

The report uses local pipeline outputs before Snowflake or Power BI so the reporting workflow can be validated without external infrastructure.

### 2026-09-20 - Phase 4 Step 2 R AUM Growth Analysis

R is used for a focused statistical analysis artifact rather than the whole pipeline because the project's main system logic already lives in Python and SQL. This keeps R in the role where it is strongest for the portfolio story: concise model summaries, confidence intervals, and residual diagnostics.

The model includes limitations because synthetic data can demonstrate analysis workflow but cannot support real-world adviser behavior claims.

The output should not be oversold as production machine learning. It is exploratory finance analysis that supports the reporting and QA context while the seeded-error detection and evaluation layer remains the main technical depth.

### 2026-09-20 - Phase 4 Step 3 Power BI-Ready Reporting Layer

We are not claiming a finished Power BI dashboard because the repository does not contain a real `.pbix` file. The honest artifact at this stage is a Power BI-ready handoff layer: CSV exports, semantic model documentation, DAX measures, and a dashboard layout.

CSV exports are useful because they let a reviewer manually build or inspect a dashboard prototype without Snowflake credentials, while keeping the output small enough for a portfolio repository.

Snowflake remains the intended production reporting source because governed reporting should eventually read from warehouse views rather than local generated CSV files.

### 2026-09-20 - Phase 5 Step 1 Portfolio Communication Polish

This phase focused on portfolio communication and interview readiness rather than adding another core feature.

The README was reorganized around business value and the measured QA depth story: seeded ground truth, hard-rule and statistical detection, precision/recall evaluation, and reviewer workload tradeoffs.

Limitations were kept explicit to avoid overselling. The repo still does not claim a live Snowflake deployment or a finished Power BI `.pbix` file.

## Validation Notes

## Next Steps
