from pathlib import Path
from uuid import uuid4

import pandas as pd

from qa.hard_rules import detection_result_columns
from qa.statistical_rules import (
    calculate_mom_aum_growth,
    detect_iqr_aum_growth_anomalies,
    detect_iqr_revenue_anomalies,
    detect_zscore_aum_growth_anomalies,
    detect_zscore_revenue_anomalies,
    planned_methods,
    run_statistical_detection,
    save_statistical_detection_results,
)


def _performance_history() -> pd.DataFrame:
    rows = []
    ending_values = [100, 102, 104, 106, 108, 110, 112, 240]
    revenue_values = [10, 11, 10, 11, 10, 11, 10, 90]
    previous = 98
    for index, (ending_aum, revenue) in enumerate(zip(ending_values, revenue_values), start=1):
        rows.append(
            {
                "performance_id": f"PERF-{index:03d}",
                "account_id": "ACCT-001",
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "month_end_date": f"2026-{index:02d}-28",
                "beginning_aum": previous,
                "ending_aum": float(ending_aum),
                "net_new_assets": 0.0,
                "revenue": float(revenue),
                "fee_rate": 0.01,
                "source_type": "synthetic_corrupted",
                "generated_at": "2026-01-01T00:00:00",
            }
        )
        previous = ending_aum
    return pd.DataFrame(rows)


def _smooth_performance_history() -> pd.DataFrame:
    rows = []
    previous = 100.0
    for index in range(1, 9):
        ending_aum = previous * 1.02
        rows.append(
            {
                "performance_id": f"CLEAN-{index:03d}",
                "account_id": "ACCT-001",
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "month_end_date": f"2026-{index:02d}-28",
                "beginning_aum": previous,
                "ending_aum": ending_aum,
                "net_new_assets": 0.0,
                "revenue": 10.0,
                "fee_rate": 0.01,
                "source_type": "synthetic",
                "generated_at": "2026-01-01T00:00:00",
            }
        )
        previous = ending_aum
    return pd.DataFrame(rows)


def test_statistical_methods_are_declared():
    assert planned_methods() == ("z_score", "iqr")


def test_calculate_mom_aum_growth_adds_growth_column():
    result = calculate_mom_aum_growth(_performance_history(), group_cols=["advisor_id"])

    assert "mom_aum_growth" in result.columns
    assert result["mom_aum_growth"].notna().sum() == len(result) - 1


def test_clean_generated_data_produces_zero_or_few_conservative_detections():
    detections = run_statistical_detection(
        _smooth_performance_history(),
        z_threshold=10.0,
        iqr_multiplier=10.0,
    )

    assert detections.empty


def test_extreme_positive_aum_jump_is_detected():
    detections = detect_iqr_aum_growth_anomalies(
        _performance_history(),
        multiplier=1.5,
        group_level="advisor",
    )

    assert "iqr_aum_growth_anomaly" in set(detections["rule_name"])
    assert (detections["field_name"] == "mom_aum_growth").all()


def test_extreme_negative_aum_jump_is_detected():
    performance = _performance_history()
    performance.loc[7, "ending_aum"] = 50.0

    detections = detect_iqr_aum_growth_anomalies(
        performance,
        multiplier=1.5,
        group_level="advisor",
    )

    assert "iqr_aum_growth_anomaly" in set(detections["rule_name"])


def test_revenue_spike_is_detected():
    detections = detect_iqr_revenue_anomalies(
        _performance_history(),
        multiplier=1.5,
        group_level="advisor",
    )

    assert "iqr_revenue_anomaly" in set(detections["rule_name"])
    assert (detections["field_name"] == "revenue").all()


def test_zscore_threshold_parameter_changes_detection_count():
    performance = _performance_history()

    sensitive = detect_zscore_revenue_anomalies(performance, threshold=2.0, group_level="advisor")
    conservative = detect_zscore_revenue_anomalies(performance, threshold=10.0, group_level="advisor")

    assert len(sensitive) > len(conservative)


def test_iqr_multiplier_parameter_changes_detection_count():
    performance = _performance_history()

    sensitive = detect_iqr_aum_growth_anomalies(performance, multiplier=1.5, group_level="advisor")
    conservative = detect_iqr_aum_growth_anomalies(performance, multiplier=10000.0, group_level="advisor")

    assert len(sensitive) > len(conservative)


def test_output_schema_and_detection_family_are_statistical_rule():
    detections = run_statistical_detection(
        _performance_history(),
        z_threshold=2.0,
        iqr_multiplier=1.5,
    )

    assert list(detections.columns) == detection_result_columns()
    assert set(detections["detection_family"]) == {"statistical_rule"}
    assert detections.loc[0, "detection_id"] == "STAT-000001"


def test_run_statistical_detection_does_not_mutate_input_dataframe():
    performance = _performance_history()
    before = performance.copy(deep=True)

    run_statistical_detection(performance, z_threshold=2.0, iqr_multiplier=1.5)

    pd.testing.assert_frame_equal(performance, before)


def test_save_statistical_detection_results_writes_csv_to_temporary_directory():
    output_dir = Path("data") / "qa" / "detections" / f"test_{uuid4().hex}"
    detections = run_statistical_detection(
        _performance_history(),
        z_threshold=2.0,
        iqr_multiplier=1.5,
    )

    try:
        output_path = save_statistical_detection_results(detections, output_dir=output_dir)

        assert output_path.exists()
        assert output_path.name == "statistical_detection_results.csv"
    finally:
        for file_path in output_dir.glob("*"):
            file_path.unlink()
        if output_dir.exists():
            output_dir.rmdir()


def test_small_groups_are_handled_without_crashing():
    small_group = _performance_history().head(3)

    detections = run_statistical_detection(small_group, z_threshold=2.0, iqr_multiplier=1.5)

    assert detections.empty
    assert list(detections.columns) == detection_result_columns()


def test_zscore_aum_growth_anomalies_can_run_at_branch_level():
    detections = detect_zscore_aum_growth_anomalies(
        _performance_history(),
        threshold=2.0,
        group_level="branch",
    )

    assert set(detections["detection_family"]).issubset({"statistical_rule"})
