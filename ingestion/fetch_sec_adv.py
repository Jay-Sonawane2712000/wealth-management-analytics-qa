"""Offline SEC/IAPD Form ADV firm ingestion utilities.

The module normalizes a user-supplied official/local CSV or creates a clearly
labeled development sample. It does not scrape websites, use the network, or
write to Snowflake.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd

SEC_ADV_TARGET_TABLE = "RAW.SEC_ADV_FIRMS"
NORMALIZED_COLUMNS = [
    "firm_crd_number",
    "firm_name",
    "sec_number",
    "registration_status",
    "registration_state",
    "main_office_city",
    "main_office_state",
    "main_office_zip",
    "regulatory_aum",
    "employee_count",
    "branch_count",
    "source_type",
    "source_file",
    "ingested_at",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "sec_adv" / "sec_adv_firms_sample.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "sec_adv_firms_normalized.csv"

COLUMN_ALIASES = {
    "firm_crd_number": [
        "firm_crd_number", "crd_number", "firm_crd", "crd", "firmcrd",
        "firm_crd_no", "firm_crd_num", "crd_no", "crd_num", "organization_crd",
    ],
    "firm_name": [
        "firm_name", "adviser_name", "advisor_name", "ia_firm_name",
        "organization_name", "primary_business_name", "legal_name", "registrant_name",
    ],
    "sec_number": [
        "sec_number", "sec_file_number", "file_number", "sec_registration_number",
        "sec_no", "sec_file_no", "sec_number_801",
    ],
    "registration_status": [
        "registration_status", "status", "firm_status", "registrationstatus",
        "current_status", "registration_status_description",
    ],
    "registration_state": [
        "registration_state", "state_registered", "jurisdiction",
        "registration_jurisdiction", "registered_state", "registration_state_code",
    ],
    "main_office_city": [
        "main_office_city", "city", "main_city", "office_city", "principal_office_city",
        "main_address_city", "principal_city",
    ],
    "main_office_state": [
        "main_office_state", "state", "main_state", "office_state",
        "principal_office_state", "main_address_state", "principal_state",
    ],
    "main_office_zip": [
        "main_office_zip", "zip", "zipcode", "zip_code", "postal_code",
        "principal_office_zip", "main_address_zip", "main_office_postal_code",
    ],
    "regulatory_aum": [
        "regulatory_aum", "aum", "assets_under_management", "ra_um",
        "regulatory_assets", "regulatory_assets_under_management",
        "total_regulatory_assets_under_management", "total_aum", "assets_under_mgmt",
    ],
    "employee_count": [
        "employee_count", "employees", "number_of_employees", "total_employees",
        "employee_total", "number_employees",
    ],
    "branch_count": [
        "branch_count", "branches", "number_of_branches", "office_count",
        "number_of_offices", "total_offices", "other_office_count",
    ],
}


def planned_target_table() -> str:
    """Return the planned Snowflake target table for public adviser data."""
    return SEC_ADV_TARGET_TABLE


def get_default_sec_adv_path() -> Path:
    """Return the default local SEC ADV sample-file path."""
    return DEFAULT_INPUT_PATH


def load_sec_adv_file(path: str | Path) -> pd.DataFrame:
    """Read a local SEC/IAPD-style CSV file.

    The raw SEC/IAPD exports can vary by source and preparation method, so this
    function only reads the file. Column standardization happens separately in
    normalize_sec_adv_columns.
    """
    return pd.read_csv(path, dtype=str)


def normalize_sec_adv_columns(
    df: pd.DataFrame,
    source_type: str,
    source_file: str | Path,
) -> pd.DataFrame:
    """Normalize plausible SEC/IAPD-style columns into the project schema."""
    if source_type not in {"real_sec_adv_file", "development_sample"}:
        raise ValueError("source_type must be real_sec_adv_file or development_sample")

    column_lookup = {_clean_column_name(str(column)): column for column in df.columns}
    normalized = pd.DataFrame(
        {
            target: _pick_column(df, column_lookup, aliases)
            for target, aliases in COLUMN_ALIASES.items()
        }
    )

    text_columns = [
        "firm_name", "registration_status", "main_office_city", "main_office_zip",
    ]
    for column in text_columns:
        normalized[column] = _to_clean_string(normalized[column])

    normalized["firm_crd_number"] = _to_identifier(normalized["firm_crd_number"])
    normalized["sec_number"] = _to_identifier(normalized["sec_number"])
    normalized["registration_state"] = _to_state(normalized["registration_state"])
    normalized["main_office_state"] = _to_state(normalized["main_office_state"])
    normalized["regulatory_aum"] = _to_number(normalized["regulatory_aum"])
    normalized["employee_count"] = _to_integer(normalized["employee_count"])
    normalized["branch_count"] = _to_integer(normalized["branch_count"])
    normalized["source_type"] = source_type
    normalized["source_file"] = str(source_file)
    normalized["ingested_at"] = datetime.now(timezone.utc).isoformat()

    return normalized[NORMALIZED_COLUMNS]


def generate_development_sample(row_count: int = 30) -> pd.DataFrame:
    """Create clearly labeled development sample data for offline work.

    These rows are realistic enough to exercise the ingestion interface, but
    they are not official SEC/IAPD records.
    """
    if row_count < 1:
        raise ValueError("row_count must be at least 1")

    firm_roots = [
        "Northstar", "Cedar Ridge", "Summit Harbor", "Blue Oak", "Evergreen",
        "Pinnacle", "Riverbend", "Meridian", "Atlas", "Keystone",
    ]
    firm_suffixes = [
        "Wealth Advisors", "Capital Management", "Investment Counsel",
        "Financial Partners", "Advisory Group",
    ]
    states = [
        ("New York", "NY", "10022"),
        ("Chicago", "IL", "60606"),
        ("Austin", "TX", "78701"),
        ("Denver", "CO", "80202"),
        ("San Francisco", "CA", "94105"),
        ("Boston", "MA", "02110"),
        ("Phoenix", "AZ", "85004"),
        ("Charlotte", "NC", "28202"),
    ]

    rows = []
    for index in range(row_count):
        city, state, zip_code = states[index % len(states)]
        rows.append(
            {
                "firm_crd_number": str(100000 + index),
                "firm_name": f"{firm_roots[index % len(firm_roots)]} {firm_suffixes[index % len(firm_suffixes)]}",
                "sec_number": f"801-{70000 + index}",
                "registration_status": "Approved",
                "registration_state": state,
                "main_office_city": city,
                "main_office_state": state,
                "main_office_zip": zip_code,
                "regulatory_aum": 250_000_000 + (index * 37_500_000),
                "employee_count": 12 + (index % 18),
                "branch_count": 1 + (index % 6),
            }
        )

    return normalize_sec_adv_columns(
        pd.DataFrame(rows),
        source_type="development_sample",
        source_file="generated_development_sample",
    )


def build_sec_adv_firms_dataset(
    input_path: str | Path | None = None,
    allow_sample_fallback: bool = True,
    state_filter: str | None = None,
    max_rows: int | None = None,
    sort_by_aum: bool = True,
) -> pd.DataFrame:
    """Build, filter, sort, and optionally sample a normalized firm dataset."""
    _validate_max_rows(max_rows)
    path = Path(input_path) if input_path is not None else get_default_sec_adv_path()

    if path.exists():
        raw_df = load_sec_adv_file(path)
        dataset = normalize_sec_adv_columns(
            raw_df,
            source_type="real_sec_adv_file",
            source_file=path,
        )
        input_mode = "official/local file"
    elif allow_sample_fallback:
        dataset = generate_development_sample()
        input_mode = "development sample"
    else:
        raise FileNotFoundError(f"No SEC ADV input file found at {path}")

    return _prepare_dataset(
        dataset,
        input_mode=input_mode,
        row_count_before=len(dataset),
        state_filter=state_filter,
        max_rows=max_rows,
        sort_by_aum=sort_by_aum,
    )


def save_sec_adv_firms_dataset(
    output_path: str | Path | None = None,
    input_path: str | Path | None = None,
    allow_sample_fallback: bool = True,
    state_filter: str | None = None,
    max_rows: int | None = None,
    sort_by_aum: bool = True,
) -> Path:
    """Build and save the normalized SEC ADV firms dataset as a CSV file."""
    path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    dataset = build_sec_adv_firms_dataset(
        input_path=input_path,
        allow_sample_fallback=allow_sample_fallback,
        state_filter=state_filter,
        max_rows=max_rows,
        sort_by_aum=sort_by_aum,
    )
    dataset.to_csv(path, index=False)
    return path


def _clean_column_name(column_name: str) -> str:
    """Convert a messy source column name into a simple matching key."""
    cleaned = column_name.lstrip("\ufeff").strip().casefold()
    for character in [" ", "\t", "\n", "-", ".", "/", "\\", "(", ")", "#", ":"]:
        cleaned = cleaned.replace(character, "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


def _pick_column(
    df: pd.DataFrame,
    column_lookup: dict[str, str],
    candidates: list[str],
) -> pd.Series:
    """Return the first matching source column, or missing values."""
    for candidate in candidates:
        source_column = column_lookup.get(candidate)
        if source_column is not None:
            return df[source_column]
    return pd.Series([pd.NA] * len(df), index=df.index)


def _to_number(series: pd.Series) -> pd.Series:
    """Convert currency-like values to numeric values."""
    cleaned = series.astype("string").str.strip()
    negative = cleaned.str.match(r"^\(.*\)$", na=False)
    cleaned = cleaned.str.replace(r"[$,%()]", "", regex=True).str.replace(r"\s+", "", regex=True)
    cleaned = cleaned.where(~negative, "-" + cleaned)
    return pd.to_numeric(cleaned, errors="coerce")


def _to_integer(series: pd.Series) -> pd.Series:
    """Convert count-like values to nullable integers where possible."""
    numeric = _to_number(series)
    return numeric.round().astype("Int64")


def _to_clean_string(series: pd.Series) -> pd.Series:
    """Trim strings and represent blanks as missing values."""
    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned.eq(""), pd.NA)


def _to_identifier(series: pd.Series) -> pd.Series:
    """Keep CRD and SEC identifiers as strings without spreadsheet .0 suffixes."""
    cleaned = _to_clean_string(series)
    return cleaned.str.replace(r"\.0$", "", regex=True)


def _to_state(series: pd.Series) -> pd.Series:
    """Normalize state or jurisdiction codes for case-insensitive filtering."""
    return _to_clean_string(series).str.upper()


def _validate_max_rows(max_rows: int | None) -> None:
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows must be at least 1")


def _prepare_dataset(
    dataset: pd.DataFrame,
    *,
    input_mode: str,
    row_count_before: int,
    state_filter: str | None,
    max_rows: int | None,
    sort_by_aum: bool,
) -> pd.DataFrame:
    """Apply deterministic filters and retain CLI reporting metadata."""
    prepared = dataset.copy()
    if state_filter:
        state = state_filter.strip().upper()
        registration_match = prepared["registration_state"].fillna("").str.upper().eq(state)
        office_match = prepared["main_office_state"].fillna("").str.upper().eq(state)
        prepared = prepared.loc[registration_match | office_match]

    if sort_by_aum:
        prepared = prepared.sort_values(
            "regulatory_aum", ascending=False, na_position="last", kind="stable"
        )

    if max_rows is not None:
        prepared = prepared.head(max_rows)

    prepared = prepared.reset_index(drop=True)
    source_file = str(dataset["source_file"].iloc[0]) if not dataset.empty else "(empty input)"
    source_type = (
        str(dataset["source_type"].iloc[0])
        if not dataset.empty
        else ("development_sample" if input_mode == "development sample" else "real_sec_adv_file")
    )
    prepared.attrs["ingestion_metadata"] = {
        "input_mode": input_mode,
        "source_file": source_file,
        "row_count_before_filtering": row_count_before,
        "row_count_after_filtering_sampling": len(prepared),
        "source_type": source_type,
    }
    return prepared


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser without executing ingestion."""
    parser = argparse.ArgumentParser(description="Normalize a local SEC/IAPD adviser firm CSV.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="Path to an official/local SEC/IAPD CSV.")
    source.add_argument("--use-sample", action="store_true", help="Use the offline development sample.")
    parser.add_argument("--state", dest="state_filter", help="Keep firms registered or based in this state code.")
    parser.add_argument("--max-rows", type=int, help="Keep at most this many rows after sorting.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Normalized CSV output path.")
    parser.add_argument("--no-sort-by-aum", action="store_true", help="Preserve source order instead of sorting by AUM.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run local ingestion and write its compact quality report."""
    from ingestion.sec_adv_quality import write_sec_adv_quality_report

    args = create_parser().parse_args(argv)
    if args.use_sample:
        _validate_max_rows(args.max_rows)
        dataset = generate_development_sample()
        dataset = _prepare_dataset(
            dataset,
            input_mode="development sample",
            row_count_before=len(dataset),
            state_filter=args.state_filter,
            max_rows=args.max_rows,
            sort_by_aum=not args.no_sort_by_aum,
        )
    else:
        dataset = build_sec_adv_firms_dataset(
            input_path=args.input,
            allow_sample_fallback=args.input is None,
            state_filter=args.state_filter,
            max_rows=args.max_rows,
            sort_by_aum=not args.no_sort_by_aum,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False)
    write_sec_adv_quality_report(dataset)

    metadata = dataset.attrs["ingestion_metadata"]
    print(f"Input mode used: {metadata['input_mode']}")
    print(f"Source file: {metadata['source_file']}")
    print(f"Row count before filtering: {metadata['row_count_before_filtering']}")
    print(f"Row count after filtering/sampling: {metadata['row_count_after_filtering_sampling']}")
    print(f"Output path: {args.output}")
    print(f"source_type value: {metadata['source_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
