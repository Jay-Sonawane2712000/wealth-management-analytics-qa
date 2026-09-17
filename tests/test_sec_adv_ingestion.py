import pandas as pd
from pandas.api.types import is_numeric_dtype
from pathlib import Path
from uuid import uuid4

from ingestion.fetch_sec_adv import (
    NORMALIZED_COLUMNS,
    build_sec_adv_firms_dataset,
    generate_development_sample,
    normalize_sec_adv_columns,
    save_sec_adv_firms_dataset,
)


def test_development_fallback_returns_expected_columns():
    dataset = build_sec_adv_firms_dataset(
        input_path="missing_sec_adv_file.csv",
        allow_sample_fallback=True,
    )

    assert list(dataset.columns) == NORMALIZED_COLUMNS
    assert len(dataset) == 30


def test_development_fallback_source_type_is_labeled():
    dataset = generate_development_sample(row_count=5)

    assert set(dataset["source_type"]) == {"development_sample"}


def test_firm_crd_number_is_string_like():
    dataset = generate_development_sample(row_count=5)

    assert str(dataset["firm_crd_number"].dtype) == "string"
    assert all(isinstance(value, str) for value in dataset["firm_crd_number"].dropna())


def test_regulatory_aum_is_numeric():
    dataset = generate_development_sample(row_count=5)

    assert is_numeric_dtype(dataset["regulatory_aum"])


def test_save_sec_adv_firms_dataset_writes_csv():
    output_path = Path("data") / "processed" / f"test_sec_adv_{uuid4().hex}.csv"

    try:
        saved_path = save_sec_adv_firms_dataset(output_path)

        assert saved_path == output_path
        assert output_path.exists()
        saved = pd.read_csv(output_path)
        assert list(saved.columns) == NORMALIZED_COLUMNS
    finally:
        if output_path.exists():
            output_path.unlink()


def test_normalize_handles_messy_plausible_sec_column_names():
    raw = pd.DataFrame(
        {
            "Firm CRD #": ["12345"],
            "Primary Business Name": ["Example Fiduciary Advisors"],
            "SEC File Number": ["801-12345"],
            "Status": ["Approved"],
            "Jurisdiction": ["CA"],
            "Principal Office City": ["Los Angeles"],
            "Principal Office State": ["CA"],
            "Principal Office ZIP": ["90071"],
            "Assets Under Management": ["$1,250,000,000"],
            "Number of Employees": ["42"],
            "Number of Branches": ["3"],
        }
    )

    normalized = normalize_sec_adv_columns(
        raw,
        source_type="real_sec_adv_file",
        source_file="unit_test_sample.csv",
    )

    assert normalized.loc[0, "firm_crd_number"] == "12345"
    assert normalized.loc[0, "firm_name"] == "Example Fiduciary Advisors"
    assert normalized.loc[0, "regulatory_aum"] == 1250000000
    assert normalized.loc[0, "employee_count"] == 42
    assert normalized.loc[0, "branch_count"] == 3
    assert normalized.loc[0, "source_type"] == "real_sec_adv_file"
