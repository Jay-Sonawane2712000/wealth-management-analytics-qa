from pathlib import Path
from uuid import uuid4

import pandas as pd

from qa.evaluate import (
    combine_detection_results,
    evaluate_detection_results,
    matched_record_columns,
    metric_columns,
    normalize_detection_rule_name,
    run_threshold_comparison,
    save_evaluation_outputs,
)
from qa.inject_errors import planned_ground_truth_table
from qa.run_local_qa_pipeline import run_local_qa_pipeline


def _ground_truth() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "performance_id": "PERF-001",
                "error_type": "negative_revenue",
                "detection_family": "hard_rule",
            },
            {
                "performance_id": "PERF-002",
                "error_type": "extreme_revenue_spike",
                "detection_family": "statistical_rule",
            },
            {
                "performance_id": "PERF-003",
                "error_type": "negative_ending_aum",
                "detection_family": "hard_rule",
            },
        ]
    )


def _detections() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "detection_id": "HARD-000001",
                "rule_name": "negative_revenue",
                "detection_family": "hard_rule",
                "performance_id": "PERF-001",
            },
            {
                "detection_id": "STAT-000001",
                "rule_name": "zscore_revenue_anomaly",
                "detection_family": "statistical_rule",
                "performance_id": "PERF-002",
            },
            {
                "detection_id": "HARD-000002",
                "rule_name": "negative_revenue",
                "detection_family": "hard_rule",
                "performance_id": "PERF-999",
            },
        ]
    )


def _threshold_performance() -> pd.DataFrame:
    rows = []
    endings = [100, 102, 104, 106, 108, 110, 112, 240]
    revenues = [10, 11, 10, 11, 10, 11, 10, 90]
    previous = 98
    for index, (ending, revenue) in enumerate(zip(endings, revenues), start=1):
        rows.append(
            {
                "performance_id": f"PERF-{index:03d}",
                "account_id": "ACCT-001",
                "advisor_id": "ADV-001",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "month_end_date": f"2026-{index:02d}-28",
                "beginning_aum": previous,
                "ending_aum": float(ending),
                "net_new_assets": 0.0,
                "revenue": float(revenue),
                "fee_rate": 0.01,
            }
        )
        previous = ending
    return pd.DataFrame(rows)


def test_metric_and_match_columns_return_expected_schema():
    assert "precision" in metric_columns()
    assert "recall" in metric_columns()
    assert matched_record_columns() == [
        "performance_id",
        "error_type",
        "rule_name",
        "detection_family",
        "match_status",
        "threshold_label",
        "explanation",
    ]


def test_exact_hard_rule_matching_produces_true_positive():
    _, matches = evaluate_detection_results(_ground_truth(), _detections())

    matched = matches[matches["performance_id"] == "PERF-001"].iloc[0]
    assert matched["match_status"] == "true_positive"


def test_statistical_detection_matches_by_family_and_performance_id():
    _, matches = evaluate_detection_results(_ground_truth(), _detections())

    matched = matches[matches["performance_id"] == "PERF-002"].iloc[0]
    assert matched["match_status"] == "true_positive"
    assert matched["rule_name"] == "zscore_revenue_anomaly"


def test_false_positives_and_false_negatives_are_counted():
    metrics, matches = evaluate_detection_results(_ground_truth(), _detections())
    overall = metrics[metrics["evaluation_scope"] == "overall"].iloc[0]

    assert overall["true_positives"] == 2
    assert overall["false_positives"] == 1
    assert overall["false_negatives"] == 1
    assert "false_positive" in set(matches["match_status"])
    assert "false_negative" in set(matches["match_status"])


def test_duplicate_detections_do_not_inflate_true_positives():
    duplicate_detections = pd.concat([_detections(), _detections().head(1)], ignore_index=True)

    metrics, _ = evaluate_detection_results(_ground_truth(), duplicate_detections)
    overall = metrics[metrics["evaluation_scope"] == "overall"].iloc[0]

    assert overall["true_positives"] == 2
    assert overall["false_positives"] == 2


def test_precision_recall_false_positive_rate_and_f1_are_calculated_correctly():
    metrics, _ = evaluate_detection_results(_ground_truth(), _detections())
    overall = metrics[metrics["evaluation_scope"] == "overall"].iloc[0]

    assert overall["precision"] == 2 / 3
    assert overall["recall"] == 2 / 3
    assert overall["false_positive_rate"] == 1 / 3
    assert overall["f1_score"] == 2 / 3


def test_combine_detection_results_combines_multiple_frames():
    combined = combine_detection_results(_detections().head(1), _detections().tail(1))

    assert len(combined) == 2


def test_save_evaluation_outputs_writes_both_csvs():
    metrics, matches = evaluate_detection_results(_ground_truth(), _detections())
    output_dir = Path("data") / "qa" / "evaluation" / f"test_{uuid4().hex}"

    try:
        paths = save_evaluation_outputs(metrics, matches, output_dir=output_dir)

        assert paths["metrics"].exists()
        assert paths["matches"].exists()
    finally:
        for file_path in output_dir.glob("*"):
            file_path.unlink()
        if output_dir.exists():
            output_dir.rmdir()


def test_run_threshold_comparison_returns_multiple_threshold_labels():
    ground_truth = pd.DataFrame(
        [
            {
                "performance_id": "PERF-008",
                "error_type": "extreme_revenue_spike",
                "detection_family": "statistical_rule",
            }
        ]
    )

    metrics = run_threshold_comparison(
        _threshold_performance(),
        ground_truth,
        pd.DataFrame(),
        z_thresholds=(2.0, 3.0),
        iqr_multipliers=(1.5, 3.0),
    )

    assert {"z=2.0_iqr=1.5", "z=3.0_iqr=3.0"}.issubset(set(metrics["threshold_label"]))


def test_empty_detections_produce_zero_precision_and_recall_safely():
    metrics, matches = evaluate_detection_results(_ground_truth(), pd.DataFrame())
    overall = metrics[metrics["evaluation_scope"] == "overall"].iloc[0]

    assert overall["precision"] == 0
    assert overall["recall"] == 0
    assert set(matches["match_status"]) == {"false_negative"}


def test_empty_ground_truth_is_handled_safely():
    metrics, matches = evaluate_detection_results(pd.DataFrame(), _detections())
    overall = metrics[metrics["evaluation_scope"] == "overall"].iloc[0]

    assert overall["true_positives"] == 0
    assert overall["false_positives"] == len(_detections())
    assert set(matches["match_status"]) == {"false_positive"}


def test_normalize_detection_rule_name_maps_statistical_labels():
    assert normalize_detection_rule_name("zscore_revenue_anomaly") == "statistical_revenue_anomaly"
    assert normalize_detection_rule_name("extreme_revenue_spike") == "statistical_revenue_anomaly"


def test_scaffold_tables_and_pipeline_import_are_available():
    assert planned_ground_truth_table() == "QA.GROUND_TRUTH_INJECTED_ERRORS"
    assert callable(run_local_qa_pipeline)
