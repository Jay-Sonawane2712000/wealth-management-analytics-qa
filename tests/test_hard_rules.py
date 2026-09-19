from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from qa.hard_rules import (
    detection_result_columns,
    run_hard_rule_detection,
    save_detection_results,
)


@pytest.fixture(scope="module")
def clean_datasets():
    branches = pd.DataFrame(
        [
            {
                "branch_id": "BR-001",
                "firm_crd_number": "100001",
                "branch_name": "Test Branch",
                "branch_city": "Phoenix",
                "branch_state": "AZ",
                "branch_region": "West",
                "opened_date": "2020-01-01",
                "is_active": True,
                "source_type": "synthetic",
                "generated_at": "2026-01-01T00:00:00",
            }
        ]
    )
    advisors = pd.DataFrame(
        [
            {
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "advisor_name": "Alex Advisor",
                "advisor_tenure_years": 5,
                "primary_client_segment": "affluent",
                "is_active": True,
                "start_date": "2021-01-01",
                "source_type": "synthetic",
                "generated_at": "2026-01-01T00:00:00",
            }
        ]
    )
    accounts = pd.DataFrame(
        [
            {
                "account_id": "ACCT-001",
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "client_segment": "affluent",
                "account_open_date": "2022-01-01",
                "account_status": "active",
                "source_type": "synthetic",
                "generated_at": "2026-01-01T00:00:00",
            },
            {
                "account_id": "ACCT-002",
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "client_segment": "affluent",
                "account_open_date": "2022-01-01",
                "account_status": "closed",
                "source_type": "synthetic",
                "generated_at": "2026-01-01T00:00:00",
            },
        ]
    )
    performance = pd.DataFrame(
        [
            {
                "performance_id": "PERF-001",
                "account_id": "ACCT-001",
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "month_end_date": "2026-08-31",
                "beginning_aum": 100000.0,
                "ending_aum": 102000.0,
                "net_new_assets": 500.0,
                "revenue": 100.0,
                "fee_rate": 0.0100,
                "source_type": "synthetic",
                "generated_at": "2026-01-01T00:00:00",
            },
            {
                "performance_id": "PERF-002",
                "account_id": "ACCT-002",
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "month_end_date": "2026-08-31",
                "beginning_aum": 50000.0,
                "ending_aum": 0.0,
                "net_new_assets": -50000.0,
                "revenue": 0.0,
                "fee_rate": 0.0100,
                "source_type": "synthetic",
                "generated_at": "2026-01-01T00:00:00",
            },
        ]
    )
    return {
        "synthetic_branches": branches,
        "synthetic_advisors": advisors,
        "synthetic_accounts": accounts,
        "synthetic_monthly_performance": performance,
    }


def _run(performance, accounts, advisors, branches):
    return run_hard_rule_detection(performance, accounts, advisors, branches)


def test_clean_generated_data_produces_zero_hard_rule_detections(clean_datasets):
    detections = _run(
        clean_datasets["synthetic_monthly_performance"],
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert detections.empty
    assert list(detections.columns) == detection_result_columns()


def test_negative_ending_aum_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "ending_aum"] = -1

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "negative_ending_aum" in set(detections["rule_name"])


def test_negative_revenue_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "revenue"] = -1

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "negative_revenue" in set(detections["rule_name"])


def test_high_fee_rate_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "fee_rate"] = 0.035

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "invalid_fee_rate_high" in set(detections["rule_name"])


def test_low_fee_rate_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "fee_rate"] = 0.001

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "invalid_fee_rate_low" in set(detections["rule_name"])


def test_duplicate_account_month_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    duplicate = performance.iloc[0].copy()
    duplicate["performance_id"] = "PERF-DUPLICATE"
    performance = pd.concat([performance, duplicate.to_frame().T], ignore_index=True)

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "duplicate_account_month" in set(detections["rule_name"])


def test_revenue_on_closed_account_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    accounts = clean_datasets["synthetic_accounts"].copy(deep=True)
    account_id = performance.loc[0, "account_id"]
    accounts.loc[accounts["account_id"] == account_id, "account_status"] = "closed"
    performance.loc[0, "revenue"] = 100

    detections = _run(
        performance,
        accounts,
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "revenue_on_closed_account" in set(detections["rule_name"])


def test_missing_account_reference_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "account_id"] = "ACCT-MISSING"

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "missing_account_reference" in set(detections["rule_name"])


def test_missing_advisor_reference_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "advisor_id"] = "ADV-MISSING"

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "missing_advisor_reference" in set(detections["rule_name"])


def test_missing_branch_reference_is_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "branch_id"] = "BR-MISSING"

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "missing_branch_reference" in set(detections["rule_name"])


def test_null_key_fields_are_detected(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "performance_id"] = pd.NA

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert "null_key_fields" in set(detections["rule_name"])


def test_output_schema_matches_expected_detection_columns(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    performance.loc[0, "revenue"] = -1

    detections = _run(
        performance,
        clean_datasets["synthetic_accounts"],
        clean_datasets["synthetic_advisors"],
        clean_datasets["synthetic_branches"],
    )

    assert list(detections.columns) == detection_result_columns()
    assert detections.loc[0, "detection_id"] == "HARD-000001"
    assert set(detections["detection_family"]) == {"hard_rule"}


def test_save_detection_results_writes_csv_to_temporary_directory():
    output_dir = Path("data") / "qa" / "detections" / f"test_{uuid4().hex}"
    detections = pd.DataFrame([{column: "example" for column in detection_result_columns()}])

    try:
        output_path = save_detection_results(detections, output_dir=output_dir)

        assert output_path.exists()
        assert output_path.name == "hard_rule_detection_results.csv"
    finally:
        for file_path in output_dir.glob("*"):
            file_path.unlink()
        if output_dir.exists():
            output_dir.rmdir()


def test_run_hard_rule_detection_does_not_mutate_inputs(clean_datasets):
    performance = clean_datasets["synthetic_monthly_performance"].copy(deep=True)
    accounts = clean_datasets["synthetic_accounts"].copy(deep=True)
    advisors = clean_datasets["synthetic_advisors"].copy(deep=True)
    branches = clean_datasets["synthetic_branches"].copy(deep=True)
    performance_before = performance.copy(deep=True)
    accounts_before = accounts.copy(deep=True)
    advisors_before = advisors.copy(deep=True)
    branches_before = branches.copy(deep=True)

    run_hard_rule_detection(performance, accounts, advisors, branches)

    pd.testing.assert_frame_equal(performance, performance_before)
    pd.testing.assert_frame_equal(accounts, accounts_before)
    pd.testing.assert_frame_equal(advisors, advisors_before)
    pd.testing.assert_frame_equal(branches, branches_before)
