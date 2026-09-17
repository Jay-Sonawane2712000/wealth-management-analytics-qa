"""Credential-safe Snowflake loader for normalized SEC ADV firm data.

This module prepares the future RAW.SEC_ADV_FIRMS load path without requiring a
live Snowflake account during tests. It reads credentials from environment
variables, validates the normalized CSV shape, and connects only when all
required Snowflake settings are present.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is listed in requirements.
    def load_dotenv() -> bool:
        """Fallback no-op when python-dotenv is not installed."""
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "sec_adv_firms_normalized.csv"
REQUIRED_CONFIG_KEYS = [
    "account",
    "user",
    "password",
    "role",
    "warehouse",
    "database",
    "schema",
]
REQUIRED_COLUMNS = [
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


def get_snowflake_config() -> dict[str, str | None]:
    """Load Snowflake connection settings from local environment variables."""
    load_dotenv()
    return {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }


def validate_snowflake_config(config: dict[str, str | None]) -> None:
    """Raise a friendly error when required Snowflake credentials are missing."""
    missing = [key for key in REQUIRED_CONFIG_KEYS if not config.get(key)]
    if missing:
        missing_names = ", ".join(f"SNOWFLAKE_{key.upper()}" for key in missing)
        raise ValueError(
            "Snowflake credentials are not configured. "
            f"Missing: {missing_names}. Add these to a local .env file and do not commit it."
        )


def get_connection(config: dict[str, str | None]):
    """Create a Snowflake connection after config validation."""
    validate_snowflake_config(config)

    import snowflake.connector

    return snowflake.connector.connect(
        account=config["account"],
        user=config["user"],
        password=config["password"],
        role=config["role"],
        warehouse=config["warehouse"],
        database=config["database"],
        schema=config["schema"],
    )


def validate_sec_adv_dataframe(df: pd.DataFrame) -> None:
    """Validate that the normalized SEC ADV DataFrame is load-ready."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"SEC ADV dataset is missing required columns: {', '.join(missing)}")


def load_dataframe_to_sec_adv_firms(df: pd.DataFrame, connection) -> int:
    """Insert normalized SEC ADV rows into RAW.SEC_ADV_FIRMS.

    The explicit INSERT keeps the loader beginner-readable and makes the target
    table clear. Later phases can replace this with staged COPY or write_pandas
    if larger files require it.
    """
    validate_sec_adv_dataframe(df)
    load_df = df[REQUIRED_COLUMNS].where(pd.notna(df[REQUIRED_COLUMNS]), None)

    insert_sql = """
        INSERT INTO RAW.SEC_ADV_FIRMS (
            FIRM_CRD_NUMBER,
            FIRM_NAME,
            SEC_NUMBER,
            REGISTRATION_STATUS,
            REGISTRATION_STATE,
            MAIN_OFFICE_CITY,
            MAIN_OFFICE_STATE,
            MAIN_OFFICE_ZIP,
            REGULATORY_AUM,
            EMPLOYEE_COUNT,
            BRANCH_COUNT,
            SOURCE_TYPE,
            SOURCE_FILE,
            INGESTED_AT
        )
        VALUES (
            %(firm_crd_number)s,
            %(firm_name)s,
            %(sec_number)s,
            %(registration_status)s,
            %(registration_state)s,
            %(main_office_city)s,
            %(main_office_state)s,
            %(main_office_zip)s,
            %(regulatory_aum)s,
            %(employee_count)s,
            %(branch_count)s,
            %(source_type)s,
            %(source_file)s,
            %(ingested_at)s
        )
    """

    rows: list[dict[str, Any]] = load_df.to_dict(orient="records")
    if not rows:
        return 0

    cursor = connection.cursor()
    try:
        cursor.executemany(insert_sql, rows)
    finally:
        cursor.close()

    return len(rows)


def load_sec_adv_csv_to_snowflake(csv_path: str | Path | None = None) -> int:
    """Read the normalized SEC ADV CSV and load it to Snowflake when configured."""
    config = get_snowflake_config()
    validate_snowflake_config(config)

    path = Path(csv_path) if csv_path is not None else DEFAULT_CSV_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Normalized SEC ADV CSV was not found at {path}. "
            "Run the local SEC ADV ingestion step before loading to Snowflake."
        )

    df = pd.read_csv(path, dtype={"firm_crd_number": "string", "main_office_zip": "string"})
    validate_sec_adv_dataframe(df)

    connection = get_connection(config)
    try:
        return load_dataframe_to_sec_adv_firms(df, connection)
    finally:
        connection.close()


if __name__ == "__main__":
    loaded_rows = load_sec_adv_csv_to_snowflake()
    print(f"Loaded {loaded_rows} rows into RAW.SEC_ADV_FIRMS.")
