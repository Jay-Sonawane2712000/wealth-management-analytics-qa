# AI Workflow Log

## Objective

## Prompts and Decisions

### 2026-09-17 - Phase 1 Step 2 SEC ADV Ingestion

We added bounded SEC ADV firm ingestion instead of trying to ingest the full adviser universe at this stage. The module is designed for a portfolio-friendly sample workflow that can normalize a local SEC/IAPD-style CSV into the future `RAW.SEC_ADV_FIRMS` structure.

We also added a development fallback sample so tests and repository structure can work before downloading or staging official files. The fallback is explicitly labeled with `source_type = "development_sample"` to avoid misrepresenting generated sample rows as real regulatory data.

Real SEC adviser firm data remains separated from future synthetic advisor, account, and performance data for governance and interpretability.

## Validation Notes

## Next Steps
