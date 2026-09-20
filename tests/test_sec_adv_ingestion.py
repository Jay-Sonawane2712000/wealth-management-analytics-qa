import pandas as pd
from pandas.api.types import is_numeric_dtype
from pathlib import Path
from uuid import uuid4

from ingestion.fetch_sec_adv import (
    NORMALIZED_COLUMNS,
    build_sec_adv_firms_dataset,
    create_parser,
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


def test_alias_mapping_is_case_insensitive_and_parses_formatted_numbers():
    raw = pd.DataFrame(
        {
            "  FIRM CRD NO  ": [12345.0],
            "LEGAL NAME": [" Example Advisors "],
            "SEC NO": ["801-012345"],
            "TOTAL REGULATORY ASSETS UNDER MANAGEMENT": ["$2,500,000"],
            "TOTAL EMPLOYEES": ["1,234"],
            "TOTAL OFFICES": ["12"],
        }
    )

    normalized = normalize_sec_adv_columns(raw, "real_sec_adv_file", "messy.csv")

    assert normalized.loc[0, "firm_crd_number"] == "12345"
    assert normalized.loc[0, "firm_name"] == "Example Advisors"
    assert normalized.loc[0, "sec_number"] == "801-012345"
    assert normalized.loc[0, "regulatory_aum"] == 2500000
    assert normalized.loc[0, "employee_count"] == 1234
    assert normalized.loc[0, "branch_count"] == 12


def test_real_file_state_filter_sort_and_max_rows():
    input_path = Path("pytest_tmp") / f"official_local_{uuid4().hex}.csv"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        pd.DataFrame(
            {
                "Firm CRD #": ["1", "2", "3", "4"],
                "Firm Name": ["A", "B", "C", "D"],
                "Registration State": ["AZ", "CA", "az", "AZ"],
                "Regulatory AUM": ["100", "900", "300", "200"],
            }
        ).to_csv(input_path, index=False)

        dataset = build_sec_adv_firms_dataset(
            input_path=input_path,
            allow_sample_fallback=False,
            state_filter="az",
            max_rows=2,
            sort_by_aum=True,
        )

        assert dataset["firm_crd_number"].tolist() == ["3", "4"]
        assert dataset["regulatory_aum"].tolist() == [300, 200]
        assert set(dataset["source_type"]) == {"real_sec_adv_file"}
        assert dataset.attrs["ingestion_metadata"]["row_count_before_filtering"] == 4
        assert dataset.attrs["ingestion_metadata"]["row_count_after_filtering_sampling"] == 2
    finally:
        if input_path.exists():
            input_path.unlink()


def test_fallback_sample_honors_max_rows_and_aum_sort():
    dataset = build_sec_adv_firms_dataset(
        input_path="missing_sec_adv_file.csv",
        allow_sample_fallback=True,
        max_rows=4,
    )

    assert len(dataset) == 4
    assert dataset["regulatory_aum"].is_monotonic_decreasing
    assert set(dataset["source_type"]) == {"development_sample"}


def test_cli_parser_can_be_imported_without_running_ingestion():
    args = create_parser().parse_args(["--use-sample", "--max-rows", "5"])

    assert args.use_sample is True
    assert args.max_rows == 5


def test_sec_adv_ingestion_docs_include_commands():
    project_root = Path(__file__).resolve().parents[1]
    guide = (project_root / "docs" / "sec_adv_ingestion_guide.md").read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "python -m ingestion.fetch_sec_adv --input data/raw/sec_adv/my_file.csv --state AZ --max-rows 300" in guide
    assert "python -m ingestion.fetch_sec_adv --use-sample --max-rows 30" in guide
    assert "python -m ingestion.fetch_sec_adv" in readme
