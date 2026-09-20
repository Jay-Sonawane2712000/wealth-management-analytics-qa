# SEC ADV/IAPD Local File Ingestion Guide

## Scope

This workflow normalizes an official SEC/IAPD adviser firm CSV that you obtain separately and place under `data/raw/sec_adv/`. It is an offline, bounded ingestion path: it does not scrape SEC or IAPD websites, download files, connect to Snowflake, or claim full production ingestion.

The input should contain public firm-level fields such as a firm CRD number, firm name, SEC number, registration status or jurisdiction, main-office location, regulatory assets under management, employee count, or office/branch count. Common column-name variations, casing, and whitespace are normalized by the ingestion module.

## Raw File Handling

Place a local official CSV at a path such as:

```text
data/raw/sec_adv/my_file.csv
```

Raw SEC/IAPD CSV files are ignored by git because official exports can be large, may be refreshed independently, and should retain their original source provenance outside the repository. Do not force-add them. Normalized CSV outputs under `data/processed/` are also reproducible and ignored.

## Normalize an Official/Local File

From the repository root, run:

```bash
python -m ingestion.fetch_sec_adv --input data/raw/sec_adv/my_file.csv --state AZ --max-rows 300
```

The command performs case-insensitive alias matching, trims source column names, parses AUM and count fields, retains CRD and SEC identifiers as strings, filters to the requested state, sorts by regulatory AUM by default, and then applies the row limit. State filtering accepts a state code and matches either registration state or main-office state.

To choose the normalized output path explicitly:

```bash
python -m ingestion.fetch_sec_adv --input data/raw/sec_adv/my_file.csv --state AZ --max-rows 300 --output data/processed/sec_adv_firms_normalized.csv
```

The CLI prints the input mode, source file, row counts before and after filtering/sampling, output path, and `source_type`. Rows from a supplied file are labeled `real_sec_adv_file`.

## Use the Offline Development Sample

No official file is needed to exercise the workflow:

```bash
python -m ingestion.fetch_sec_adv --use-sample --max-rows 30
```

Development rows are labeled `development_sample`. They are not official SEC/IAPD records and must not be presented as real firm observations.

## Inspect the Quality Report

Each CLI run writes `reports/sec_adv_ingestion_quality.md`. Review it for:

- total rows and unique firm CRD numbers;
- missing CRD numbers, firm names, and regulatory AUM;
- counts by registration state;
- the top 10 firms by regulatory AUM; and
- the `source_type` breakdown.

The committed report is generated only from development sample data and says so prominently. If you run the command with an official file, review the newly generated report locally before deciding whether it is appropriate and small enough to commit.

## Governance Boundary

Official SEC/IAPD inputs represent real public adviser firm-level data. They remain separate from the project's synthetic private-style branch, advisor, account, and monthly performance data. The local ingestion path does not create or imply real client, account, advisor, or performance records.
