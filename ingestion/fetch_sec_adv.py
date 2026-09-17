"""Local SEC/IAPD Form ADV firm ingestion utilities.

This module prepares a bounded adviser-firm dataset for the future
RAW.SEC_ADV_FIRMS Snowflake table. It supports two local development paths:

1. Real-file mode: read a CSV staged at data/raw/sec_adv/sec_adv_firms_sample.csv.
2. Development fallback mode: generate clearly labeled sample rows when no
   local file is available.

No network calls or Snowflake writes happen in this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

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

    column_lookup = {_clean_column_name(column): column for column in df.columns}

    normalized = pd.DataFrame(
        {
            "firm_crd_number": _pick_column(
                df,
                column_lookup,
                ["firm_crd_number", "crd_number", "firm_crd", "crd", "firmcrd"],
            ),
            "firm_name": _pick_column(
                df,
                column_lookup,
                ["firm_name", "adviser_name", "ia_firm_name", "organization_name", "primary_business_name"],
            ),
            "sec_number": _pick_column(
                df,
                column_lookup,
                ["sec_number", "sec_file_number", "file_number", "sec_registration_number"],
            ),
            "registration_status": _pick_column(
                df,
                column_lookup,
                ["registration_status", "status", "firm_status", "registrationstatus"],
            ),
            "registration_state": _pick_column(
                df,
                column_lookup,
                ["registration_state", "state_registered", "jurisdiction", "registration_jurisdiction"],
            ),
            "main_office_city": _pick_column(
                df,
                column_lookup,
                ["main_office_city", "city", "main_city", "office_city", "principal_office_city"],
            ),
            "main_office_state": _pick_column(
                df,
                column_lookup,
                ["main_office_state", "state", "main_state", "office_state", "principal_office_state"],
            ),
            "main_office_zip": _pick_column(
                df,
                column_lookup,
                ["main_office_zip", "zip", "zipcode", "postal_code", "principal_office_zip"],
            ),
            "regulatory_aum": _pick_column(
                df,
                column_lookup,
                ["regulatory_aum", "aum", "assets_under_management", "ra_um", "regulatory_assets"],
            ),
            "employee_count": _pick_column(
                df,
                column_lookup,
                ["employee_count", "employees", "number_of_employees", "total_employees"],
            ),
            "branch_count": _pick_column(
                df,
                column_lookup,
                ["branch_count", "branches", "number_of_branches", "office_count"],
            ),
        }
    )

    normalized["firm_crd_number"] = normalized["firm_crd_number"].astype("string").str.strip()
    normalized["main_office_zip"] = normalized["main_office_zip"].astype("string").str.strip()
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
) -> pd.DataFrame:
    """Build the normalized local SEC ADV firms dataset."""
    path = Path(input_path) if input_path is not None else get_default_sec_adv_path()

    if path.exists():
        raw_df = load_sec_adv_file(path)
        return normalize_sec_adv_columns(
            raw_df,
            source_type="real_sec_adv_file",
            source_file=path,
        )

    if allow_sample_fallback:
        return generate_development_sample()

    raise FileNotFoundError(f"No SEC ADV input file found at {path}")


def save_sec_adv_firms_dataset(output_path: str | Path | None = None) -> Path:
    """Build and save the normalized SEC ADV firms dataset as a CSV file."""
    path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    dataset = build_sec_adv_firms_dataset()
    dataset.to_csv(path, index=False)
    return path


def _clean_column_name(column_name: str) -> str:
    """Convert a messy source column name into a simple matching key."""
    cleaned = column_name.strip().lower()
    for character in [" ", "-", ".", "/", "\\", "(", ")", "#"]:
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
    cleaned = series.astype("string").str.replace(r"[$,]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def _to_integer(series: pd.Series) -> pd.Series:
    """Convert count-like values to nullable integers where possible."""
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.round().astype("Int64")
