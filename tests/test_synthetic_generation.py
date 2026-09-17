import pandas as pd

from ingestion.generate_synthetic import (
    ACCOUNT_COLUMNS,
    ADVISOR_COLUMNS,
    BRANCH_COLUMNS,
    PERFORMANCE_COLUMNS,
    generate_all_synthetic_data,
)


EXPECTED_DATASETS = {
    "synthetic_branches",
    "synthetic_advisors",
    "synthetic_accounts",
    "synthetic_monthly_performance",
}


def _small_datasets():
    return generate_all_synthetic_data(seed=123, months=3)


def test_generate_all_synthetic_data_returns_expected_datasets():
    datasets = _small_datasets()

    assert set(datasets) == EXPECTED_DATASETS


def test_each_dataset_has_expected_columns():
    datasets = _small_datasets()

    assert list(datasets["synthetic_branches"].columns) == BRANCH_COLUMNS
    assert list(datasets["synthetic_advisors"].columns) == ADVISOR_COLUMNS
    assert list(datasets["synthetic_accounts"].columns) == ACCOUNT_COLUMNS
    assert list(datasets["synthetic_monthly_performance"].columns) == PERFORMANCE_COLUMNS


def test_source_type_is_synthetic_for_all_generated_datasets():
    datasets = _small_datasets()

    for dataset in datasets.values():
        assert set(dataset["source_type"]) == {"synthetic"}


def test_monthly_performance_financial_values_are_realistic():
    performance = _small_datasets()["synthetic_monthly_performance"]

    assert (performance["revenue"] >= 0).all()
    assert performance["fee_rate"].between(0.0025, 0.0150).all()
    assert (performance["ending_aum"] >= 0).all()


def test_generation_is_reproducible_with_same_seed():
    first = generate_all_synthetic_data(seed=777, months=2)
    second = generate_all_synthetic_data(seed=777, months=2)

    for name in EXPECTED_DATASETS:
        pd.testing.assert_frame_equal(first[name], second[name])


def test_monthly_performance_references_valid_parent_records():
    datasets = _small_datasets()
    accounts = datasets["synthetic_accounts"]
    performance = datasets["synthetic_monthly_performance"]

    account_keys = set(
        accounts[["account_id", "advisor_id", "branch_id"]].itertuples(index=False, name=None)
    )
    performance_keys = set(
        performance[["account_id", "advisor_id", "branch_id"]].itertuples(index=False, name=None)
    )

    assert performance_keys.issubset(account_keys)
    assert set(performance["account_id"]).issubset(set(accounts["account_id"]))
    assert set(accounts["advisor_id"]).issubset(set(datasets["synthetic_advisors"]["advisor_id"]))
    assert set(accounts["branch_id"]).issubset(set(datasets["synthetic_branches"]["branch_id"]))
