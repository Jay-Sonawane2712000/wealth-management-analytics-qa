import pandas as pd
import pytest
from pathlib import Path
from uuid import uuid4

from ingestion import load_sec_adv_to_snowflake as loader


def _valid_sec_adv_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "firm_crd_number": "12345",
                "firm_name": "Example Fiduciary Advisors",
                "sec_number": "801-12345",
                "registration_status": "Approved",
                "registration_state": "CA",
                "main_office_city": "Los Angeles",
                "main_office_state": "CA",
                "main_office_zip": "90071",
                "regulatory_aum": 1250000000.00,
                "employee_count": 42,
                "branch_count": 3,
                "source_type": "real_sec_adv_file",
                "source_file": "unit_test_sample.csv",
                "ingested_at": "2026-09-17T00:00:00+00:00",
            }
        ]
    )


def test_get_snowflake_config_returns_expected_keys(monkeypatch):
    for key in loader.REQUIRED_CONFIG_KEYS:
        monkeypatch.delenv(f"SNOWFLAKE_{key.upper()}", raising=False)
    monkeypatch.setattr(loader, "load_dotenv", lambda: False)

    config = loader.get_snowflake_config()

    assert set(config) == set(loader.REQUIRED_CONFIG_KEYS)


def test_validate_snowflake_config_detects_missing_credentials():
    config = {key: "" for key in loader.REQUIRED_CONFIG_KEYS}

    with pytest.raises(ValueError, match="Snowflake credentials are not configured"):
        loader.validate_snowflake_config(config)


def test_validate_sec_adv_dataframe_accepts_required_columns():
    loader.validate_sec_adv_dataframe(_valid_sec_adv_dataframe())


def test_validate_sec_adv_dataframe_rejects_missing_required_columns():
    invalid_df = _valid_sec_adv_dataframe().drop(columns=["firm_crd_number"])

    with pytest.raises(ValueError, match="missing required columns"):
        loader.validate_sec_adv_dataframe(invalid_df)


def test_load_sec_adv_csv_to_snowflake_fails_before_connecting_when_credentials_missing(
    monkeypatch,
):
    csv_path = Path("data") / "processed" / f"test_sec_adv_loader_{uuid4().hex}.csv"

    for key in loader.REQUIRED_CONFIG_KEYS:
        monkeypatch.delenv(f"SNOWFLAKE_{key.upper()}", raising=False)
    monkeypatch.setattr(loader, "load_dotenv", lambda: False)

    def fail_if_connection_attempted(config):
        raise AssertionError("Loader should not attempt a Snowflake connection")

    monkeypatch.setattr(loader, "get_connection", fail_if_connection_attempted)

    try:
        _valid_sec_adv_dataframe().to_csv(csv_path, index=False)

        with pytest.raises(ValueError, match="Snowflake credentials are not configured"):
            loader.load_sec_adv_csv_to_snowflake(csv_path)
    finally:
        if csv_path.exists():
            csv_path.unlink()
