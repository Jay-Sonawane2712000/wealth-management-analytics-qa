from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from ingestion.generate_synthetic import generate_all_synthetic_data
from qa.inject_errors import (
    EXPECTED_ERROR_TYPES,
    GROUND_TRUTH_COLUMNS,
    inject_seeded_errors,
    save_injected_error_outputs,
)


def _small_error_plan():
    return {error_type: 2 for error_type in EXPECTED_ERROR_TYPES}


@pytest.fixture(scope="module")
def baseline_datasets():
    return generate_all_synthetic_data(seed=909, months=3, validate=True)


@pytest.fixture(scope="module")
def injected_outputs(baseline_datasets):
    return inject_seeded_errors(baseline_datasets, error_plan=_small_error_plan(), seed=101)


def test_inject_seeded_errors_returns_corrupted_performance_and_ground_truth(injected_outputs):
    corrupted, ground_truth = injected_outputs
    assert isinstance(corrupted, pd.DataFrame)
    assert isinstance(ground_truth, pd.DataFrame)
    assert not ground_truth.empty


def test_ground_truth_has_required_columns(injected_outputs):
    _, ground_truth = injected_outputs
    assert list(ground_truth.columns) == GROUND_TRUTH_COLUMNS


def test_all_expected_error_types_can_be_injected(injected_outputs):
    _, ground_truth = injected_outputs
    assert set(EXPECTED_ERROR_TYPES).issubset(set(ground_truth["error_type"]))


def test_ground_truth_contains_hard_and_statistical_detection_families(injected_outputs):
    _, ground_truth = injected_outputs
    assert {"hard_rule", "statistical_rule"}.issubset(set(ground_truth["detection_family"]))


def test_corrupted_performance_has_at_least_as_many_rows_as_clean_performance(
    baseline_datasets,
    injected_outputs,
):
    clean_row_count = len(baseline_datasets["synthetic_monthly_performance"])
    corrupted, _ = injected_outputs

    assert len(corrupted) >= clean_row_count


def test_clean_input_performance_is_not_mutated_in_place(baseline_datasets):
    datasets = {name: dataset.copy(deep=True) for name, dataset in baseline_datasets.items()}
    clean_before = datasets["synthetic_monthly_performance"].copy(deep=True)

    inject_seeded_errors(datasets, error_plan=_small_error_plan(), seed=101)

    pd.testing.assert_frame_equal(datasets["synthetic_monthly_performance"], clean_before)


def test_same_seed_produces_reproducible_ground_truth(baseline_datasets):
    _, first = inject_seeded_errors(baseline_datasets, error_plan=_small_error_plan(), seed=202)
    _, second = inject_seeded_errors(baseline_datasets, error_plan=_small_error_plan(), seed=202)

    pd.testing.assert_frame_equal(first, second)


def test_negative_ending_aum_errors_create_negative_values(injected_outputs):
    corrupted, ground_truth = injected_outputs
    error_ids = ground_truth.loc[
        ground_truth["error_type"] == "negative_ending_aum",
        "performance_id",
    ]

    values = corrupted.loc[corrupted["performance_id"].isin(error_ids), "ending_aum"]

    assert (values < 0).all()


def test_negative_revenue_errors_create_negative_values(injected_outputs):
    corrupted, ground_truth = injected_outputs
    error_ids = ground_truth.loc[
        ground_truth["error_type"] == "negative_revenue",
        "performance_id",
    ]

    values = corrupted.loc[corrupted["performance_id"].isin(error_ids), "revenue"]

    assert (values < 0).all()


def test_invalid_fee_rate_high_errors_create_high_fee_rates(injected_outputs):
    corrupted, ground_truth = injected_outputs
    error_ids = ground_truth.loc[
        ground_truth["error_type"] == "invalid_fee_rate_high",
        "performance_id",
    ]

    values = corrupted.loc[corrupted["performance_id"].isin(error_ids), "fee_rate"]

    assert (values > 0.0150).all()


def test_duplicate_account_month_creates_duplicate_account_month_combinations(injected_outputs):
    corrupted, _ = injected_outputs
    duplicate_count = corrupted.duplicated(["account_id", "month_end_date"]).sum()

    assert duplicate_count >= _small_error_plan()["duplicate_account_month"]


def test_saved_outputs_write_to_temporary_directory(injected_outputs):
    corrupted, ground_truth = injected_outputs
    output_dir = Path("data") / "raw" / "synthetic_corrupted" / f"test_{uuid4().hex}"

    try:
        paths = save_injected_error_outputs(corrupted, ground_truth, output_dir=output_dir)

        assert paths["synthetic_monthly_performance_corrupted"].exists()
        assert paths["ground_truth_injected_errors"].exists()
    finally:
        for file_path in output_dir.glob("*"):
            file_path.unlink()
        if output_dir.exists():
            output_dir.rmdir()
