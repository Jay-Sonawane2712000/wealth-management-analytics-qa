import pandas as pd
import pytest

from ingestion.generate_synthetic import generate_all_synthetic_data, load_firm_seed_data
from qa.validate_synthetic_integrity import run_synthetic_integrity_checks


@pytest.fixture(scope="module")
def clean_datasets():
    return generate_all_synthetic_data(seed=321, months=2, validate=False)


@pytest.fixture(scope="module")
def firm_seed_data():
    return load_firm_seed_data(max_firms=30)


def _copy_datasets(datasets):
    return {name: dataset.copy(deep=True) for name, dataset in datasets.items()}


def test_clean_generated_datasets_produce_no_validation_issues(clean_datasets, firm_seed_data):
    issues = run_synthetic_integrity_checks(clean_datasets, firms=firm_seed_data)

    assert list(issues.columns) == ["check_name", "severity", "issue_count", "details"]
    assert issues.empty


def test_missing_required_columns_are_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    datasets["synthetic_accounts"] = datasets["synthetic_accounts"].drop(columns=["advisor_id"])

    issues = run_synthetic_integrity_checks(datasets)

    assert "required_columns" in set(issues["check_name"])


def test_invalid_source_type_is_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    datasets["synthetic_branches"].loc[0, "source_type"] = "real_sec_adv_file"

    issues = run_synthetic_integrity_checks(datasets)

    assert "source_type" in set(issues["check_name"])


def test_broken_advisor_to_branch_link_is_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    datasets["synthetic_advisors"].loc[0, "branch_id"] = "BR-MISSING"

    issues = run_synthetic_integrity_checks(datasets)

    assert "advisor_branch_links" in set(issues["check_name"])


def test_broken_account_to_advisor_link_is_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    datasets["synthetic_accounts"].loc[0, "advisor_id"] = "ADV-MISSING"

    issues = run_synthetic_integrity_checks(datasets)

    assert "account_advisor_links" in set(issues["check_name"])


def test_broken_performance_to_account_link_is_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    datasets["synthetic_monthly_performance"].loc[0, "account_id"] = "ACCT-MISSING"

    issues = run_synthetic_integrity_checks(datasets)

    assert "performance_account_links" in set(issues["check_name"])


def test_negative_aum_and_revenue_values_are_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    performance = datasets["synthetic_monthly_performance"]
    performance.loc[0, "beginning_aum"] = -1
    performance.loc[1, "ending_aum"] = -1
    performance.loc[2, "revenue"] = -1

    issues = run_synthetic_integrity_checks(datasets)

    check_names = set(issues["check_name"])
    assert "negative_beginning_aum" in check_names
    assert "negative_ending_aum" in check_names
    assert "negative_revenue" in check_names


def test_fee_rates_outside_expected_range_are_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    datasets["synthetic_monthly_performance"].loc[0, "fee_rate"] = 0.0200

    issues = run_synthetic_integrity_checks(datasets)

    assert "fee_rate_range" in set(issues["check_name"])


def test_missing_ending_aum_is_reported(clean_datasets):
    datasets = _copy_datasets(clean_datasets)
    datasets["synthetic_monthly_performance"].loc[0, "ending_aum"] = pd.NA

    issues = run_synthetic_integrity_checks(datasets)

    assert "missing_ending_aum" in set(issues["check_name"])


def test_generate_all_synthetic_data_validate_true_succeeds_for_clean_data():
    datasets = generate_all_synthetic_data(seed=654, months=1, validate=True)

    assert set(datasets) == {
        "synthetic_branches",
        "synthetic_advisors",
        "synthetic_accounts",
        "synthetic_monthly_performance",
    }


def test_generate_all_synthetic_data_validate_false_still_works():
    datasets = generate_all_synthetic_data(seed=654, months=1, validate=False)

    assert not datasets["synthetic_monthly_performance"].empty
