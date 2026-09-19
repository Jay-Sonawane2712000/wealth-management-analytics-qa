"""Markdown reporting helpers for local QA evaluation outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "reports" / "generated_qa_summary.md"
RUN_TIMESTAMP = "2026-09-18"


def select_overall_metrics(metrics_df: pd.DataFrame) -> pd.Series:
    """Return the overall metrics row from an evaluation metrics DataFrame."""
    if metrics_df.empty:
        return pd.Series(dtype="object")
    overall = metrics_df[metrics_df["evaluation_scope"] == "overall"]
    if overall.empty:
        return metrics_df.iloc[0]
    return overall.iloc[0]


def select_operating_threshold(threshold_metrics_df: pd.DataFrame) -> str:
    """Select the threshold label with the best overall F1 score."""
    if threshold_metrics_df.empty:
        return "not_available"
    overall = threshold_metrics_df[threshold_metrics_df["evaluation_scope"] == "overall"].copy()
    if overall.empty:
        return "not_available"
    overall = overall.sort_values(
        ["f1_score", "recall", "precision"],
        ascending=[False, False, False],
    )
    return str(overall.iloc[0]["threshold_label"])


def format_threshold_table(threshold_metrics_df: pd.DataFrame) -> str:
    """Format overall threshold metrics as a Markdown table."""
    if threshold_metrics_df.empty:
        return "No threshold comparison metrics were generated."

    overall = threshold_metrics_df[threshold_metrics_df["evaluation_scope"] == "overall"].copy()
    if overall.empty:
        return "No overall threshold comparison rows were generated."

    columns = [
        "threshold_label",
        "precision",
        "recall",
        "false_positive_rate",
        "f1_score",
        "true_positives",
        "false_positives",
        "false_negatives",
    ]
    overall = overall[columns].drop_duplicates().sort_values("threshold_label")
    lines = [
        "| Threshold | Precision | Recall | False Positive Rate | F1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in overall.itertuples(index=False):
        lines.append(
            f"| {row.threshold_label} | {_fmt(row.precision)} | {_fmt(row.recall)} | "
            f"{_fmt(row.false_positive_rate)} | {_fmt(row.f1_score)} | "
            f"{int(row.true_positives)} | {int(row.false_positives)} | {int(row.false_negatives)} |"
        )
    return "\n".join(lines)


def write_generated_qa_summary(
    metrics_df: pd.DataFrame,
    threshold_metrics_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    hard_rule_results_df: pd.DataFrame,
    statistical_results_df: pd.DataFrame,
    output_path: str | Path = DEFAULT_SUMMARY_PATH,
) -> Path:
    """Write a portfolio-ready QA summary using actual local run outputs."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    overall = select_overall_metrics(metrics_df)
    selected_threshold = select_operating_threshold(threshold_metrics_df)
    error_breakdown = _value_counts_table(ground_truth_df, "error_type", "Error Type")
    threshold_table = format_threshold_table(threshold_metrics_df)

    content = f"""# Generated QA Summary

## Run Timestamp

{RUN_TIMESTAMP}

## Ground Truth Injected Error Count

Total injected errors: {len(ground_truth_df)}

## Error Type Breakdown

{error_breakdown}

## Detection Count Summary

- Hard-rule detections: {len(hard_rule_results_df)}
- Statistical detections: {len(statistical_results_df)}
- Combined detections: {len(hard_rule_results_df) + len(statistical_results_df)}

## Overall Metrics

- Precision: {_fmt(overall.get("precision", 0))}
- Recall: {_fmt(overall.get("recall", 0))}
- False-positive rate: {_fmt(overall.get("false_positive_rate", 0))}
- F1 score: {_fmt(overall.get("f1_score", 0))}
- True positives: {int(overall.get("true_positives", 0) or 0)}
- False positives: {int(overall.get("false_positives", 0) or 0)}
- False negatives: {int(overall.get("false_negatives", 0) or 0)}

## Threshold Comparison

{threshold_table}

## Selected Operating Threshold

Selected threshold: `{selected_threshold}`

## Reviewer Tradeoff Explanation

The selected threshold is the best current operating point based on generated F1 score, with recall and precision used as tie-breakers. Lower thresholds may catch more injected issues but can increase reviewer workload through false positives. Higher thresholds may reduce review volume but can allow bad finance data to reach reporting.

## Output Locations

- Detailed ignored CSV outputs: `data/qa/evaluation/` and `data/qa/detections/`
- Corrupted synthetic outputs: `data/raw/synthetic_corrupted/`
"""
    path.write_text(content, encoding="utf-8")
    return path


def _value_counts_table(df: pd.DataFrame, column: str, label: str) -> str:
    if df.empty or column not in df.columns:
        return f"| {label} | Count |\n|---|---:|\n| none | 0 |"
    counts = df[column].value_counts().sort_index()
    lines = [f"| {label} | Count |", "|---|---:|"]
    for value, count in counts.items():
        lines.append(f"| {value} | {int(count)} |")
    return "\n".join(lines)


def _fmt(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "0.000"
