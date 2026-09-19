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

## Validation Notes

## Next Steps
