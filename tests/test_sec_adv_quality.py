from pathlib import Path
from uuid import uuid4

import pandas as pd

from ingestion.sec_adv_quality import (
    profile_sec_adv_dataset,
    sec_adv_quality_columns,
    write_sec_adv_quality_report,
)


def _quality_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "firm_crd_number": ["100", "101", pd.NA, "100"],
            "firm_name": ["Alpha Advisors", "Beta Capital", "", "Alpha Advisors"],
            "regulatory_aum": [500_000_000, 250_000_000, pd.NA, 450_000_000],
            "registration_state": ["AZ", "CA", "AZ", "AZ"],
            "source_type": ["real_sec_adv_file"] * 4,
            "source_file": ["official.csv"] * 4,
        }
    )


def test_quality_columns_are_explicit():
    assert sec_adv_quality_columns() == [
        "firm_crd_number",
        "firm_name",
        "regulatory_aum",
        "registration_state",
        "source_type",
        "source_file",
    ]


def test_profile_sec_adv_dataset_returns_expected_metrics():
    profile = profile_sec_adv_dataset(_quality_fixture())

    assert profile["row_count"] == 4
    assert profile["unique_firm_crd_number_count"] == 2
    assert profile["missing_firm_crd_number_count"] == 1
    assert profile["missing_firm_name_count"] == 1
    assert profile["missing_regulatory_aum_count"] == 1
    assert profile["registration_state_counts"] == {"AZ": 3, "CA": 1}
    assert profile["source_type_breakdown"] == {"real_sec_adv_file": 4}
    assert profile["top_firms_by_regulatory_aum"][0]["firm_name"] == "Alpha Advisors"


def test_write_sec_adv_quality_report_writes_markdown():
    output_path = Path("pytest_tmp") / f"sec_adv_quality_{uuid4().hex}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        saved_path = write_sec_adv_quality_report(_quality_fixture(), output_path)

        assert saved_path == output_path
        assert output_path.exists()
        report = output_path.read_text(encoding="utf-8")
        assert "# SEC ADV Ingestion Quality Report" in report
        assert "Unique firm CRD numbers" in report
        assert "Count by Registration State" in report
        assert "Top 10 Firms by Regulatory AUM" in report
        assert "real_sec_adv_file" in report
    finally:
        if output_path.exists():
            output_path.unlink()
