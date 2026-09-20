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

5. Load synthetic tables only after deciding which generated CSVs should be uploaded.
6. Run `sql/kpi_views.sql`.
7. Run `sql/qa_views.sql`.
8. Run local QA evaluation and compare outputs before wiring reports to Snowflake.

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
- Empty local data: run the synthetic generator before loading synthetic-style records.
- Import mismatch: confirm CSV column names match the SQL table definitions and loader expectations.

## Current Status

The repo includes Snowflake DDL and a credential-safe loader scaffold, but CI does not run against a live Snowflake account. Live execution should be treated as a future deployment step.
