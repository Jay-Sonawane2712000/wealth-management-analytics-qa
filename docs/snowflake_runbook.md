# Snowflake Runbook

## Cost and Trial Warning

Do not start or use a Snowflake trial until you are ready to load and test the warehouse objects. Use the smallest practical warehouse for this portfolio project and suspend it aggressively.

Recommended warehouse settings:

```sql
CREATE WAREHOUSE IF NOT EXISTS ANALYTICS_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
```

## Required Environment Variables

Create a local `.env` file based on `.env.example`. Never commit `.env`.

Required values:

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_ROLE`
- `SNOWFLAKE_WAREHOUSE=ANALYTICS_WH`
- `SNOWFLAKE_DATABASE=WEALTH_ANALYTICS`
- `SNOWFLAKE_SCHEMA=RAW`

## Recommended Execution Order

1. Review and run `sql/schema.sql` in Snowflake.
2. Generate local synthetic data:

   ```bash
   python -m ingestion.generate_synthetic
   ```

3. Normalize or stage SEC ADV firm data if using a real local file.
4. Load normalized SEC ADV firms with:

   ```bash
   python -m ingestion.load_sec_adv_to_snowflake
   ```

5. Validate the complete generated-data load without connecting:

   ```bash
   python -m ingestion.load_project_data_to_snowflake --dry-run
   ```

6. When the dry-run passes and every destination table is empty, run the live bulk load:

   ```bash
   python -m ingestion.load_project_data_to_snowflake
   ```

7. Deploy and verify the KPI and QA views with the reusable structured-SQL runner:

   ```bash
   python -m ingestion.deploy_snowflake_views
   ```

8. Compare warehouse QA outputs with the local evaluation reports before wiring stakeholder reporting to Snowflake.

## Generated Project Data Loader

`ingestion/load_project_data_to_snowflake.py` validates all configured CSV headers and values before opening a Snowflake connection. The dry-run parses dates, timestamps, numbers, integers, booleans, blank values, and synthetic lineage labels, then reports planned rows per destination table.

The live command uses `snowflake.connector.pandas_tools.write_pandas` for bulk loading. Before the first write, it checks every configured destination table and refuses the entire load if any table contains rows. This is a duplicate-prevention guard, not an upsert workflow. It never truncates, replaces, or deletes existing data.

Configured destinations:

- `RAW.SYNTHETIC_BRANCHES`
- `RAW.SYNTHETIC_ADVISORS`
- `RAW.SYNTHETIC_ACCOUNTS`
- `RAW.SYNTHETIC_MONTHLY_PERFORMANCE`
- `RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED`
- `QA.GROUND_TRUTH_INJECTED_ERRORS`
- `QA.DETECTION_RESULTS` (combined hard-rule and statistical detections)
- `QA.EVALUATION_METRICS` (threshold comparison metrics)
- `QA.DETECTION_GROUND_TRUTH_MATCHES`

After loading, the command re-counts every target and reports loaded and verified row counts. Keep the warehouse at the smallest practical size and allow auto-suspend to stop it after the command finishes.

## What Should Be Uploaded

Appropriate for Snowflake:

- Normalized SEC ADV firm rows for `RAW.SEC_ADV_FIRMS`.
- Clearly labeled synthetic branch, advisor, account, and monthly performance records.
- QA ground truth, detections, and evaluation outputs when intentionally generated.

Do not upload:

- `.env` or credentials.
- Local cache folders.
- Inaccessible pytest temp/cache artifacts.
- Any data that is not clearly public, synthetic, or intentionally generated for this project.

## Troubleshooting

- Missing credentials: confirm `.env` exists locally and contains all required Snowflake variables.
- Permission errors: verify the role can create warehouses, databases, schemas, tables, and views.
- Warehouse cost concerns: use XS warehouse, keep `AUTO_SUSPEND=60`, and manually suspend after testing.
- Table not found: run `sql/schema.sql` before loader or view scripts.
- Empty or missing local data: regenerate the synthetic and QA output files, then rerun the dry-run before any live load.
- Import mismatch: confirm CSV column names match the SQL table definitions and loader expectations.
- Nonempty target refusal: inspect the reported table counts. The loader intentionally does not append, truncate, or deduplicate an existing target.

## Current Status

The complete workflow was executed successfully in a Snowflake Standard trial on Azure West US 2. It loaded 30 public SEC ADV firm rows and 310,275 synthetic/QA rows across nine destinations, then deployed and verified all seven KPI, reporting, and QA views. `ANALYTICS_WH` was suspended after execution. See [the live execution report](../reports/snowflake_live_execution.md) for verified counts and interpretation.

Live Snowflake remains intentionally excluded from CI because credentials must remain local, trial availability is temporary, and warehouse execution can incur cost. CI-safe coverage uses offline dry-runs and mocked connector tests instead.

## Final Validation Workflow

1. Run `python -m pytest`.
2. Run `python -m ingestion.load_project_data_to_snowflake --dry-run`; this validates inputs without connecting or changing Snowflake data.
3. If a live deployment is intentionally being validated, confirm the seven expected views and documented counts with `python -m ingestion.deploy_snowflake_views`, then confirm `ANALYTICS_WH` is suspended.
4. Regenerate the local Power BI CSV sources with `python -m reporting.export_powerbi_csvs`.
5. Follow the [Power BI refresh and visual-validation steps](../reporting/powerbi/README.md#final-validation-workflow).
