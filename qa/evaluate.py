"""Evaluate QA detections against seeded-error ground truth.

The evaluation layer turns QA from "checks exist" into measured performance.
Hard-rule detections match ground truth by performance_id and normalized
rule/error type. Statistical detections can match statistical ground truth by
performance_id and detection family because z-score and IQR rules may catch the
same injected anomaly with different labels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from qa.statistical_rules import run_statistical_detection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "qa" / "evaluation"
EVALUATED_AT = "2026-01-22T00:00:00"
EVALUATION_METRICS = ("precision", "recall", "false_positive_rate", "f1_score")
METRIC_COLUMNS = [
    "evaluation_scope",
    "detection_family",
    "rule_name",
    "threshold_label",
    "true_positives",
    "false_positives",
    "false_negatives",
    "ground_truth_count",
    "detection_count",
    "precision",
    "recall",
    "false_positive_rate",
    "f1_score",
    "evaluated_at",
]
MATCHED_RECORD_COLUMNS = [
    "performance_id",
    "error_type",
    "rule_name",
    "detection_family",
    "match_status",
    "threshold_label",
    "explanation",
]
RULE_NAME_MAP = {
    "negative_ending_aum": "negative_ending_aum",
    "negative_revenue": "negative_revenue",
    "invalid_fee_rate_high": "invalid_fee_rate_high",
    "invalid_fee_rate_low": "invalid_fee_rate_low",
    "duplicate_account_month": "duplicate_account_month",
    "revenue_on_closed_account": "revenue_on_closed_account",
    "missing_account_reference": "missing_account_reference",
    "missing_advisor_reference": "missing_advisor_reference",
    "missing_branch_reference": "missing_branch_reference",
    "null_key_fields": "null_key_fields",
    "zscore_aum_growth_anomaly": "statistical_aum_growth_anomaly",
    "iqr_aum_growth_anomaly": "statistical_aum_growth_anomaly",
    "zscore_revenue_anomaly": "statistical_revenue_anomaly",
    "iqr_revenue_anomaly": "statistical_revenue_anomaly",
    "extreme_aum_jump_positive": "statistical_aum_growth_anomaly",
    "extreme_aum_jump_negative": "statistical_aum_growth_anomaly",
    "extreme_revenue_spike": "statistical_revenue_anomaly",
}


def planned_metrics() -> tuple[str, ...]:
    """Return supported QA performance metrics."""
    return EVALUATION_METRICS


def metric_columns() -> list[str]:
    """Return the evaluation metrics schema."""
    return METRIC_COLUMNS.copy()


def matched_record_columns() -> list[str]:
    """Return the detection-to-ground-truth match schema."""
    return MATCHED_RECORD_COLUMNS.copy()


def normalize_detection_rule_name(rule_name: str) -> str:
    """Map detector rule names and injected error types to comparable labels."""
    if pd.isna(rule_name):
        return ""
    return RULE_NAME_MAP.get(str(rule_name), str(rule_name))


def prepare_ground_truth(ground_truth_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare ground truth with normalized matching fields."""
    df = ground_truth_df.copy()
    for column in ["performance_id", "error_type", "detection_family"]:
        if column not in df.columns:
            df[column] = pd.Series(dtype="object")
    df["normalized_error_type"] = df["error_type"].map(normalize_detection_rule_name)
    return df.reset_index(drop=True)


def prepare_detections(
    detection_results_df: pd.DataFrame,
    threshold_label: str = "default",
) -> pd.DataFrame:
    """Prepare detections with normalized matching fields."""
    df = detection_results_df.copy()
    for column in ["performance_id", "rule_name", "detection_family"]:
        if column not in df.columns:
            df[column] = pd.Series(dtype="object")
    df["normalized_rule_name"] = df["rule_name"].map(normalize_detection_rule_name)
    df["threshold_label"] = threshold_label
    return df.reset_index(drop=True)


def match_detections_to_ground_truth(
    ground_truth_df: pd.DataFrame,
    detection_results_df: pd.DataFrame,
    threshold_label: str = "default",
) -> pd.DataFrame:
    """Match detections to ground truth without inflating duplicate true positives."""
    ground_truth = prepare_ground_truth(ground_truth_df)
    detections = prepare_detections(detection_results_df, threshold_label=threshold_label)
    matched_gt_indices: set[int] = set()
    rows: list[dict[str, object]] = []

    for _, detection in detections.iterrows():
        match_index = _find_matching_ground_truth_index(detection, ground_truth, matched_gt_indices)
        if match_index is None:
            rows.append(
                {
                    "performance_id": detection.get("performance_id", pd.NA),
                    "error_type": "",
                    "rule_name": detection.get("rule_name", pd.NA),
                    "detection_family": detection.get("detection_family", pd.NA),
                    "match_status": "false_positive",
                    "threshold_label": threshold_label,
                    "explanation": "Detection did not match an unused ground-truth seeded error.",
                }
            )
        else:
            matched_gt_indices.add(match_index)
            truth = ground_truth.loc[match_index]
            rows.append(
                {
                    "performance_id": detection.get("performance_id", pd.NA),
                    "error_type": truth.get("error_type", pd.NA),
                    "rule_name": detection.get("rule_name", pd.NA),
                    "detection_family": detection.get("detection_family", pd.NA),
                    "match_status": "true_positive",
                    "threshold_label": threshold_label,
                    "explanation": "Detection matched a ground-truth seeded error.",
                }
            )

    for index, truth in ground_truth.iterrows():
        if index not in matched_gt_indices:
            rows.append(
                {
                    "performance_id": truth.get("performance_id", pd.NA),
                    "error_type": truth.get("error_type", pd.NA),
                    "rule_name": "",
                    "detection_family": truth.get("detection_family", pd.NA),
                    "match_status": "false_negative",
                    "threshold_label": threshold_label,
                    "explanation": "Ground-truth seeded error was not detected.",
                }
            )

    return pd.DataFrame(rows, columns=MATCHED_RECORD_COLUMNS)


def calculate_metrics(
    matched_records_df: pd.DataFrame,
    detection_results_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    threshold_label: str = "default",
) -> pd.DataFrame:
    """Calculate overall, family, and rule-level QA metrics."""
    detections = prepare_detections(detection_results_df, threshold_label)
    ground_truth = prepare_ground_truth(ground_truth_df)
    matched = matched_records_df.copy()

    rows = [
        _metric_row(
            "overall",
            "all",
            "all",
            threshold_label,
            matched,
            detections,
            ground_truth,
        )
    ]

    families = sorted(set(detections["detection_family"].dropna()) | set(ground_truth["detection_family"].dropna()))
    for family in families:
        rows.append(
            _metric_row(
                "detection_family",
                family,
                "all",
                threshold_label,
                matched[matched["detection_family"] == family],
                detections[detections["detection_family"] == family],
                ground_truth[ground_truth["detection_family"] == family],
            )
        )

    for rule_name in sorted(detections["rule_name"].dropna().unique()):
        rows.append(
            _metric_row(
                "rule",
                str(detections.loc[detections["rule_name"] == rule_name, "detection_family"].iloc[0]),
                rule_name,
                threshold_label,
                matched[matched["rule_name"] == rule_name],
                detections[detections["rule_name"] == rule_name],
                ground_truth[
                    ground_truth["normalized_error_type"] == normalize_detection_rule_name(rule_name)
                ],
            )
        )

    return pd.DataFrame(rows, columns=METRIC_COLUMNS)


def evaluate_detection_results(
    ground_truth_df: pd.DataFrame,
    detection_results_df: pd.DataFrame,
    threshold_label: str = "default",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate detections and return metrics plus matched records."""
    matched = match_detections_to_ground_truth(
        ground_truth_df,
        detection_results_df,
        threshold_label=threshold_label,
    )
    metrics = calculate_metrics(
        matched,
        detection_results_df,
        ground_truth_df,
        threshold_label=threshold_label,
    )
    return metrics, matched


def combine_detection_results(*detection_dfs: pd.DataFrame) -> pd.DataFrame:
    """Combine one or more detector outputs into a single DataFrame."""
    frames = [df for df in detection_dfs if df is not None and not df.empty]
    if not frames:
        return pd.DataFrame(columns=["detection_id", "rule_name", "detection_family", "performance_id"])
    return pd.concat(frames, ignore_index=True)


def save_evaluation_outputs(
    metrics_df: pd.DataFrame,
    matched_records_df: pd.DataFrame,
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Save evaluation metrics and record-level matches to CSV."""
    path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)
    outputs = {
        "metrics": path / "detection_evaluation_metrics.csv",
        "matches": path / "detection_ground_truth_matches.csv",
    }
    metrics_df.to_csv(outputs["metrics"], index=False)
    matched_records_df.to_csv(outputs["matches"], index=False)
    return outputs


def run_threshold_comparison(
    performance_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    hard_rule_results_df: pd.DataFrame,
    z_thresholds: tuple[float, ...] = (2.0, 2.5, 3.0),
    iqr_multipliers: tuple[float, ...] = (1.5, 2.0, 3.0),
) -> pd.DataFrame:
    """Evaluate combined hard-rule plus statistical detections across thresholds."""
    metric_frames = []
    for z_threshold in z_thresholds:
        for iqr_multiplier in iqr_multipliers:
            threshold_label = f"z={z_threshold}_iqr={iqr_multiplier}"
            statistical = run_statistical_detection(
                performance_df,
                z_threshold=z_threshold,
                iqr_multiplier=iqr_multiplier,
            )
            combined = combine_detection_results(hard_rule_results_df, statistical)
            metrics, _ = evaluate_detection_results(
                ground_truth_df,
                combined,
                threshold_label=threshold_label,
            )
            metric_frames.append(metrics)
    if not metric_frames:
        return pd.DataFrame(columns=METRIC_COLUMNS)
    return pd.concat(metric_frames, ignore_index=True)


def _find_matching_ground_truth_index(
    detection: pd.Series,
    ground_truth: pd.DataFrame,
    matched_gt_indices: set[int],
) -> int | None:
    candidates = ground_truth[
        (ground_truth["performance_id"].astype("string") == str(detection.get("performance_id")))
        & (~ground_truth.index.isin(matched_gt_indices))
    ]
    if candidates.empty:
        return None

    if detection.get("detection_family") == "statistical_rule":
        statistical = candidates[candidates["detection_family"] == "statistical_rule"]
        if not statistical.empty:
            return int(statistical.index[0])

    normalized_rule = detection.get("normalized_rule_name")
    exact = candidates[candidates["normalized_error_type"] == normalized_rule]
    if not exact.empty:
        return int(exact.index[0])
    return None


def _metric_row(
    evaluation_scope: str,
    detection_family: str,
    rule_name: str,
    threshold_label: str,
    matched_subset: pd.DataFrame,
    detection_subset: pd.DataFrame,
    ground_truth_subset: pd.DataFrame,
) -> dict[str, object]:
    true_positives = int((matched_subset["match_status"] == "true_positive").sum()) if not matched_subset.empty else 0
    false_positives = int((matched_subset["match_status"] == "false_positive").sum()) if not matched_subset.empty else 0
    false_negatives = int((matched_subset["match_status"] == "false_negative").sum()) if not matched_subset.empty else 0
    detection_count = int(len(detection_subset))
    ground_truth_count = int(len(ground_truth_subset))
    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    false_positive_rate = _safe_divide(false_positives, detection_count)
    f1_score = _safe_divide(2 * precision * recall, precision + recall)
    return {
        "evaluation_scope": evaluation_scope,
        "detection_family": detection_family,
        "rule_name": rule_name,
        "threshold_label": threshold_label,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "ground_truth_count": ground_truth_count,
        "detection_count": detection_count,
        "precision": precision,
        "recall": recall,
        "false_positive_rate": false_positive_rate,
        "f1_score": f1_score,
        "evaluated_at": EVALUATED_AT,
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)
