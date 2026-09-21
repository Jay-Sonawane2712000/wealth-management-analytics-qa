"""Validate and bulk-load generated project datasets into Snowflake.

All local files are validated before a connection is opened. Live loading is
refused when any destination table already contains rows, preventing accidental
duplicate loads. Credentials are delegated to the existing credential-safe
Snowflake connection helpers and are never printed.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import pandas as pd

from ingestion.load_sec_adv_to_snowflake import get_connection, get_snowflake_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]

STRING = "string"
DATE = "date"
TIMESTAMP = "timestamp"
INTEGER = "integer"
NUMBER = "number"
BOOLEAN = "boolean"


class ProjectDataValidationError(ValueError):
    """Raised when a local source file cannot safely map to its table."""


class NonEmptyTargetError(RuntimeError):
    """Raised before loading when one or more destination tables have rows."""


@dataclass(frozen=True)
class DatasetSpec:
    """Declarative mapping from one or more CSV files to a Snowflake table."""

    source_paths: tuple[str, ...]
    schema: str
    table: str
    columns: tuple[tuple[str, str], ...]
    allowed_source_types: frozenset[str] | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.schema}.{self.table}"

    @property
    def expected_columns(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.columns)


@dataclass
class PreparedDataset:
    """A validated, typed DataFrame ready for write_pandas."""

    spec: DatasetSpec
    dataframe: pd.DataFrame
    source_row_counts: dict[str, int]


PERFORMANCE_COLUMNS = (
    ("performance_id", STRING),
    ("account_id", STRING),
    ("advisor_id", STRING),
    ("firm_crd_number", STRING),
    ("branch_id", STRING),
    ("month_end_date", DATE),
    ("beginning_aum", NUMBER),
    ("ending_aum", NUMBER),
    ("net_new_assets", NUMBER),
    ("revenue", NUMBER),
    ("fee_rate", NUMBER),
    ("source_type", STRING),
    ("generated_at", TIMESTAMP),
)

DETECTION_COLUMNS = (
    ("detection_id", STRING),
    ("rule_name", STRING),
    ("detection_family", STRING),
    ("performance_id", STRING),
    ("account_id", STRING),
    ("advisor_id", STRING),
    ("branch_id", STRING),
    ("firm_crd_number", STRING),
    ("month_end_date", DATE),
    ("field_name", STRING),
    ("observed_value", STRING),
    ("expected_condition", STRING),
    ("severity", STRING),
    ("explanation", STRING),
    ("detected_at", TIMESTAMP),
)

EVALUATION_COLUMNS = (
    ("evaluation_scope", STRING),
    ("detection_family", STRING),
    ("rule_name", STRING),
    ("threshold_label", STRING),
    ("true_positives", INTEGER),
    ("false_positives", INTEGER),
    ("false_negatives", INTEGER),
    ("ground_truth_count", INTEGER),
    ("detection_count", INTEGER),
    ("precision", NUMBER),
    ("recall", NUMBER),
    ("false_positive_rate", NUMBER),
    ("f1_score", NUMBER),
    ("evaluated_at", TIMESTAMP),
)

DATASET_SPECS = (
    DatasetSpec(
        source_paths=("data/raw/synthetic/synthetic_branches.csv",),
        schema="RAW",
        table="SYNTHETIC_BRANCHES",
        columns=(
            ("branch_id", STRING),
            ("firm_crd_number", STRING),
            ("branch_name", STRING),
            ("branch_city", STRING),
            ("branch_state", STRING),
            ("branch_region", STRING),
            ("opened_date", DATE),
            ("is_active", BOOLEAN),
            ("source_type", STRING),
            ("generated_at", TIMESTAMP),
        ),
        allowed_source_types=frozenset({"synthetic"}),
    ),
    DatasetSpec(
        source_paths=("data/raw/synthetic/synthetic_advisors.csv",),
        schema="RAW",
        table="SYNTHETIC_ADVISORS",
        columns=(
            ("advisor_id", STRING),
            ("firm_crd_number", STRING),
            ("branch_id", STRING),
            ("advisor_name", STRING),
            ("advisor_tenure_years", NUMBER),
            ("primary_client_segment", STRING),
            ("is_active", BOOLEAN),
            ("start_date", DATE),
            ("source_type", STRING),
            ("generated_at", TIMESTAMP),
        ),
        allowed_source_types=frozenset({"synthetic"}),
    ),
    DatasetSpec(
        source_paths=("data/raw/synthetic/synthetic_accounts.csv",),
        schema="RAW",
        table="SYNTHETIC_ACCOUNTS",
        columns=(
            ("account_id", STRING),
            ("advisor_id", STRING),
            ("firm_crd_number", STRING),
            ("branch_id", STRING),
            ("client_segment", STRING),
            ("account_open_date", DATE),
            ("account_status", STRING),
            ("source_type", STRING),
            ("generated_at", TIMESTAMP),
        ),
        allowed_source_types=frozenset({"synthetic"}),
    ),
    DatasetSpec(
        source_paths=("data/raw/synthetic/synthetic_monthly_performance.csv",),
        schema="RAW",
        table="SYNTHETIC_MONTHLY_PERFORMANCE",
        columns=PERFORMANCE_COLUMNS,
        allowed_source_types=frozenset({"synthetic"}),
    ),
    DatasetSpec(
        source_paths=("data/raw/synthetic_corrupted/synthetic_monthly_performance_corrupted.csv",),
        schema="RAW",
        table="SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED",
        columns=PERFORMANCE_COLUMNS,
        allowed_source_types=frozenset({"synthetic", "synthetic_corrupted"}),
    ),
    DatasetSpec(
        source_paths=("data/raw/synthetic_corrupted/ground_truth_injected_errors.csv",),
        schema="QA",
        table="GROUND_TRUTH_INJECTED_ERRORS",
        columns=(
            ("error_id", STRING),
            ("performance_id", STRING),
            ("account_id", STRING),
            ("advisor_id", STRING),
            ("branch_id", STRING),
            ("firm_crd_number", STRING),
            ("month_end_date", DATE),
            ("error_type", STRING),
            ("field_name", STRING),
            ("original_value", STRING),
            ("corrupted_value", STRING),
            ("severity", STRING),
            ("detection_family", STRING),
            ("explanation", STRING),
            ("injected_at", TIMESTAMP),
        ),
    ),
    DatasetSpec(
        source_paths=(
            "data/qa/detections/hard_rule_detection_results.csv",
            "data/qa/detections/statistical_detection_results.csv",
        ),
        schema="QA",
        table="DETECTION_RESULTS",
        columns=DETECTION_COLUMNS,
    ),
    DatasetSpec(
        source_paths=("data/qa/evaluation/threshold_comparison_metrics.csv",),
        schema="QA",
        table="EVALUATION_METRICS",
        columns=EVALUATION_COLUMNS,
    ),
    DatasetSpec(
        source_paths=("data/qa/evaluation/detection_ground_truth_matches.csv",),
        schema="QA",
        table="DETECTION_GROUND_TRUTH_MATCHES",
        columns=(
            ("performance_id", STRING),
            ("error_type", STRING),
            ("rule_name", STRING),
            ("detection_family", STRING),
            ("match_status", STRING),
            ("threshold_label", STRING),
            ("explanation", STRING),
        ),
    ),
)


def validate_and_prepare_project_data(
    project_root: str | Path = PROJECT_ROOT,
    specs: Sequence[DatasetSpec] = DATASET_SPECS,
) -> dict[str, PreparedDataset]:
    """Validate every source file and return typed destination DataFrames."""
    root = Path(project_root)
    prepared: dict[str, PreparedDataset] = {}

    for spec in specs:
        frames: list[pd.DataFrame] = []
        source_counts: dict[str, int] = {}
        for relative_path in spec.source_paths:
            path = root / relative_path
            if not path.is_file():
                raise ProjectDataValidationError(f"Required source file is missing: {relative_path}")

            raw = pd.read_csv(path, dtype="string", keep_default_na=False)
            validate_csv_columns(raw, spec, relative_path)
            typed = prepare_dataframe(raw, spec, relative_path)
            frames.append(typed)
            source_counts[relative_path] = len(typed)

        combined = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        prepared[spec.qualified_name] = PreparedDataset(spec, combined, source_counts)

    return prepared


def validate_csv_columns(df: pd.DataFrame, spec: DatasetSpec, source_name: str) -> None:
    """Require an exact, case-sensitive source-to-schema column set."""
    duplicate_columns = df.columns[df.columns.duplicated()].tolist()
    if duplicate_columns:
        raise ProjectDataValidationError(
            f"{source_name} contains duplicate columns: {', '.join(duplicate_columns)}"
        )

    actual = set(df.columns)
    expected = set(spec.expected_columns)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected columns: {', '.join(extra)}")
        raise ProjectDataValidationError(
            f"{source_name} does not match {spec.qualified_name} ({'; '.join(details)})"
        )


def prepare_dataframe(df: pd.DataFrame, spec: DatasetSpec, source_name: str) -> pd.DataFrame:
    """Convert a validated CSV DataFrame to Snowflake-compatible values."""
    converted = pd.DataFrame(index=df.index)
    for column, kind in spec.columns:
        converted[column.upper()] = convert_series(df[column], kind, column, source_name)

    if spec.allowed_source_types is not None:
        if converted["SOURCE_TYPE"].isna().any():
            raise ProjectDataValidationError(
                f"{source_name} contains missing SOURCE_TYPE values"
            )
        source_types = {
            str(value).strip().lower()
            for value in converted["SOURCE_TYPE"].dropna().unique().tolist()
        }
        if not source_types or not source_types.issubset(spec.allowed_source_types):
            expected = ", ".join(sorted(spec.allowed_source_types))
            found = ", ".join(sorted(source_types)) or "(none)"
            raise ProjectDataValidationError(
                f"{source_name} has invalid SOURCE_TYPE values; expected {expected}, found {found}"
            )

    return converted


def convert_series(
    series: pd.Series,
    kind: str,
    column: str,
    source_name: str,
) -> pd.Series:
    """Strictly convert one source column without silently losing bad values."""
    cleaned = series.astype("string").str.strip().mask(lambda values: values.eq(""), pd.NA)

    if kind == STRING:
        return cleaned.astype(object).where(cleaned.notna(), None)

    if kind in {INTEGER, NUMBER}:
        numeric = pd.to_numeric(cleaned, errors="coerce")
        _raise_on_invalid_conversion(cleaned, numeric, column, source_name, kind)
        if kind == INTEGER:
            fractional = numeric.dropna().mod(1).ne(0)
            if fractional.any():
                raise ProjectDataValidationError(
                    f"{source_name} column {column} contains non-integer values"
                )
            return numeric.astype("Int64")
        return numeric.astype("Float64")

    if kind == BOOLEAN:
        normalized = cleaned.str.lower()
        mapping = {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
            "y": True,
            "n": False,
        }
        converted = normalized.map(mapping)
        _raise_on_invalid_conversion(cleaned, converted, column, source_name, kind)
        return converted.astype("boolean")

    if kind == DATE:
        converted = pd.to_datetime(cleaned, errors="coerce")
        _raise_on_invalid_conversion(cleaned, converted, column, source_name, kind)
        return converted.dt.date.astype(object).where(converted.notna(), None)

    if kind == TIMESTAMP:
        converted = pd.to_datetime(cleaned, errors="coerce", utc=True)
        _raise_on_invalid_conversion(cleaned, converted, column, source_name, kind)
        return converted.dt.tz_convert(None)

    raise ProjectDataValidationError(f"Unsupported type mapping {kind} for {column}")


def _raise_on_invalid_conversion(
    source: pd.Series,
    converted: pd.Series,
    column: str,
    source_name: str,
    expected_type: str,
) -> None:
    invalid_count = int((source.notna() & converted.isna()).sum())
    if invalid_count:
        raise ProjectDataValidationError(
            f"{source_name} column {column} has {invalid_count} invalid {expected_type} value(s)"
        )


def get_target_row_counts(connection, specs: Sequence[DatasetSpec] = DATASET_SPECS) -> dict[str, int]:
    """Return row counts for every hard-coded destination table."""
    counts: dict[str, int] = {}
    cursor = connection.cursor()
    try:
        for spec in specs:
            cursor.execute(f"SELECT COUNT(*) FROM {spec.qualified_name}")
            counts[spec.qualified_name] = int(cursor.fetchone()[0])
    finally:
        cursor.close()
    return counts


def ensure_all_targets_empty(connection, specs: Sequence[DatasetSpec] = DATASET_SPECS) -> None:
    """Refuse the complete workflow if any destination already has rows."""
    counts = get_target_row_counts(connection, specs)
    nonempty = {table: count for table, count in counts.items() if count != 0}
    if nonempty:
        summary = ", ".join(f"{table}={count}" for table, count in nonempty.items())
        raise NonEmptyTargetError(
            f"No data was loaded because destination tables are not empty: {summary}"
        )


def bulk_load_prepared_data(
    connection,
    database: str,
    prepared: dict[str, PreparedDataset],
    writer: Callable | None = None,
) -> dict[str, int]:
    """Bulk-load validated DataFrames with Snowflake write_pandas."""
    if writer is None:
        from snowflake.connector.pandas_tools import write_pandas

        writer = write_pandas

    loaded: dict[str, int] = {}
    for qualified_name, dataset in prepared.items():
        frame = dataset.dataframe
        if frame.empty:
            loaded[qualified_name] = 0
            continue

        success, _, written_rows, _ = writer(
            conn=connection,
            df=frame,
            table_name=dataset.spec.table,
            database=database,
            schema=dataset.spec.schema,
            quote_identifiers=False,
            auto_create_table=False,
            overwrite=False,
        )
        if not success or int(written_rows) != len(frame):
            raise RuntimeError(
                f"Bulk load verification failed for {qualified_name}: "
                f"expected {len(frame)} rows, write_pandas reported {written_rows}"
            )
        loaded[qualified_name] = int(written_rows)

    return loaded


def verify_loaded_row_counts(
    connection,
    prepared: dict[str, PreparedDataset],
) -> dict[str, int]:
    """Verify each formerly empty target equals its planned row count."""
    specs = tuple(dataset.spec for dataset in prepared.values())
    verified = get_target_row_counts(connection, specs)
    mismatches = {
        table: (len(prepared[table].dataframe), count)
        for table, count in verified.items()
        if count != len(prepared[table].dataframe)
    }
    if mismatches:
        details = ", ".join(
            f"{table}: expected {expected}, found {actual}"
            for table, (expected, actual) in mismatches.items()
        )
        raise RuntimeError(f"Post-load row-count verification failed: {details}")
    return verified


def run_live_load(
    project_root: str | Path = PROJECT_ROOT,
    writer: Callable | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    """Validate locally, guard all targets, bulk-load, and verify counts."""
    prepared = validate_and_prepare_project_data(project_root)
    config = get_snowflake_config()
    connection = get_connection(config)
    try:
        ensure_all_targets_empty(connection)
        loaded = bulk_load_prepared_data(
            connection,
            database=str(config["database"]),
            prepared=prepared,
            writer=writer,
        )
        verified = verify_loaded_row_counts(connection, prepared)
        return loaded, verified
    finally:
        connection.close()


def dry_run(project_root: str | Path = PROJECT_ROOT) -> dict[str, PreparedDataset]:
    """Validate local files and return the load plan without connecting."""
    return validate_and_prepare_project_data(project_root)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and bulk-load generated project data into Snowflake."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files and report planned row counts without connecting.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        if args.dry_run:
            prepared = dry_run()
            print("Dry run successful; no Snowflake connection was opened.")
            for table, dataset in prepared.items():
                print(f"{table}: planned rows={len(dataset.dataframe)}")
            return 0

        loaded, verified = run_live_load()
        for table in loaded:
            print(f"{table}: loaded rows={loaded[table]}, verified rows={verified[table]}")
        return 0
    except (ProjectDataValidationError, NonEmptyTargetError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Keep connector and credential details sanitized.
        error_number = getattr(exc, "errno", None)
        sqlstate = getattr(exc, "sqlstate", None)
        print(
            f"ERROR: {type(exc).__name__}; error code={error_number}; "
            f"SQLSTATE={sqlstate}; project data load did not complete.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
