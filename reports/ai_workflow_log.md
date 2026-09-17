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

## Validation Notes

## Next Steps
