"""Statistical anomaly checks for corrupted financial reporting data.

These rules detect unusual AUM growth and revenue patterns with parameterized
z-score and IQR thresholds. They are separate from deterministic hard rules and
do not calculate precision or recall; scoring against ground truth happens in a
later phase.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from qa.hard_rules import detection_result_columns

STATISTICAL_METHODS = ("z_score", "iqr")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "qa" / "detections"
DETECTED_AT = "2026-01-21T00:00:00"
MIN_GROUP_OBSERVATIONS = 6


def planned_methods() -> tuple[str, ...]:
    """Return supported statistical anomaly detection methods."""
    return STATISTICAL_METHODS


def calculate_mom_aum_growth(
    performance_df: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Calculate month-over-month AUM growth for grouped performance data."""
    groups = group_cols or ["account_id"]
    required_cols = groups + ["month_end_date", "ending_aum"]
    missing = [column for column in required_cols if column not in performance_df.columns]
    if missing:
        raise ValueError(f"Missing required columns for AUM growth: {', '.join(missing)}")

    monthly = (
        performance_df[required_cols]
        .copy()
        .assign(
            month_end_date=lambda df: pd.to_datetime(df["month_end_date"]),
            ending_aum=lambda df: pd.to_numeric(df["ending_aum"], errors="coerce"),
        )
        .groupby(groups + ["month_end_date"], as_index=False)
        .agg(ending_aum=("ending_aum", "sum"))
        .sort_values(groups + ["month_end_date"])
    )
    monthly["previous_month_ending_aum"] = monthly.groupby(groups)["ending_aum"].shift(1)
    monthly["mom_aum_growth"] = (
        (monthly["ending_aum"] - monthly["previous_month_ending_aum"])
        / monthly["previous_month_ending_aum"].replace(0, pd.NA)
    )
    monthly["month_end_date"] = monthly["month_end_date"].dt.strftime("%Y-%m-%d")
    return monthly


def detect_zscore_aum_growth_anomalies(
    performance_df: pd.DataFrame,
    threshold: float = 3.0,
    group_level: str = "advisor",
) -> pd.DataFrame:
    """Detect unusual month-over-month AUM growth with z-scores."""
    group_cols = _group_columns(group_level)
    metric_df = calculate_mom_aum_growth(performance_df, group_cols=group_cols)
    anomalous = _zscore_anomalies(metric_df, group_cols, "mom_aum_growth", threshold)
    return _detections_from_anomalies(
        performance_df,
        anomalous,
        group_cols,
        "zscore_aum_growth_anomaly",
        "mom_aum_growth",
        f"absolute z-score <= {threshold}",
        "medium",
        f"AUM growth z-score exceeded {threshold} at {group_level} level.",
    )


def detect_iqr_aum_growth_anomalies(
    performance_df: pd.DataFrame,
    multiplier: float = 1.5,
    group_level: str = "advisor",
) -> pd.DataFrame:
    """Detect unusual month-over-month AUM growth with IQR bounds."""
    group_cols = _group_columns(group_level)
    metric_df = calculate_mom_aum_growth(performance_df, group_cols=group_cols)
    anomalous = _iqr_anomalies(metric_df, group_cols, "mom_aum_growth", multiplier)
    return _detections_from_anomalies(
        performance_df,
        anomalous,
        group_cols,
        "iqr_aum_growth_anomaly",
        "mom_aum_growth",
        f"within IQR bounds using multiplier {multiplier}",
        "medium",
        f"AUM growth was outside IQR bounds at {group_level} level.",
    )


def detect_zscore_revenue_anomalies(
    performance_df: pd.DataFrame,
    threshold: float = 3.0,
    group_level: str = "advisor",
) -> pd.DataFrame:
    """Detect unusual revenue spikes or drops with z-scores."""
    group_cols = _group_columns(group_level)
    metric_df = _monthly_revenue(performance_df, group_cols)
    anomalous = _zscore_anomalies(metric_df, group_cols, "revenue", threshold)
    return _detections_from_anomalies(
        performance_df,
        anomalous,
        group_cols,
        "zscore_revenue_anomaly",
        "revenue",
        f"absolute z-score <= {threshold}",
        "medium",
        f"Revenue z-score exceeded {threshold} at {group_level} level.",
    )


def detect_iqr_revenue_anomalies(
    performance_df: pd.DataFrame,
    multiplier: float = 1.5,
    group_level: str = "advisor",
) -> pd.DataFrame:
    """Detect unusual revenue values with IQR bounds."""
    group_cols = _group_columns(group_level)
    metric_df = _monthly_revenue(performance_df, group_cols)
    anomalous = _iqr_anomalies(metric_df, group_cols, "revenue", multiplier)
    return _detections_from_anomalies(
        performance_df,
        anomalous,
        group_cols,
        "iqr_revenue_anomaly",
        "revenue",
        f"within IQR bounds using multiplier {multiplier}",
        "medium",
        f"Revenue was outside IQR bounds at {group_level} level.",
    )


def run_statistical_detection(
    performance_df: pd.DataFrame,
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
) -> pd.DataFrame:
    """Run all statistical anomaly detectors."""
    frames = [
        detect_zscore_aum_growth_anomalies(performance_df, threshold=z_threshold, group_level="advisor"),
        detect_zscore_aum_growth_anomalies(performance_df, threshold=z_threshold, group_level="branch"),
        detect_iqr_aum_growth_anomalies(performance_df, multiplier=iqr_multiplier, group_level="advisor"),
        detect_iqr_aum_growth_anomalies(performance_df, multiplier=iqr_multiplier, group_level="branch"),
        detect_zscore_revenue_anomalies(performance_df, threshold=z_threshold, group_level="advisor"),
        detect_zscore_revenue_anomalies(performance_df, threshold=z_threshold, group_level="account"),
        detect_iqr_revenue_anomalies(performance_df, multiplier=iqr_multiplier, group_level="advisor"),
        detect_iqr_revenue_anomalies(performance_df, multiplier=iqr_multiplier, group_level="account"),
    ]
    non_empty = [frame for frame in frames if not frame.empty]
    if not non_empty:
        return _detections_dataframe([])

    detections = pd.concat(non_empty, ignore_index=True)[detection_result_columns()]
    detections = detections.drop_duplicates(
        subset=["rule_name", "performance_id", "field_name", "observed_value"]
    ).reset_index(drop=True)
    detections["detection_id"] = [
        f"STAT-{index:06d}" for index in range(1, len(detections) + 1)
    ]
    return detections


def save_statistical_detection_results(
    detection_results_df: pd.DataFrame,
    output_dir: str | Path | None = None,
) -> Path:
    """Save statistical detection results to CSV."""
    path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)
    output_path = path / "statistical_detection_results.csv"
    detection_results_df.to_csv(output_path, index=False)
    return output_path


def _monthly_revenue(performance_df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    required_cols = group_cols + ["month_end_date", "revenue"]
    missing = [column for column in required_cols if column not in performance_df.columns]
    if missing:
        raise ValueError(f"Missing required columns for revenue anomalies: {', '.join(missing)}")

    monthly = (
        performance_df[required_cols]
        .copy()
        .assign(
            month_end_date=lambda df: pd.to_datetime(df["month_end_date"]),
            revenue=lambda df: pd.to_numeric(df["revenue"], errors="coerce"),
        )
        .groupby(group_cols + ["month_end_date"], as_index=False)
        .agg(revenue=("revenue", "sum"))
        .sort_values(group_cols + ["month_end_date"])
    )
    monthly["month_end_date"] = monthly["month_end_date"].dt.strftime("%Y-%m-%d")
    return monthly


def _zscore_anomalies(
    metric_df: pd.DataFrame,
    group_cols: list[str],
    metric_col: str,
    threshold: float,
) -> pd.DataFrame:
    results = []
    for _, group in metric_df.dropna(subset=[metric_col]).groupby(group_cols):
        if len(group) < MIN_GROUP_OBSERVATIONS:
            continue
        std = group[metric_col].std(ddof=0)
        if pd.isna(std) or std == 0:
            continue
        mean = group[metric_col].mean()
        scored = group.copy()
        scored["observed_metric"] = scored[metric_col]
        scored["z_score"] = (scored[metric_col] - mean) / std
        results.append(scored[scored["z_score"].abs() > threshold])
    return _concat_or_empty(results, metric_df.columns.tolist() + ["observed_metric", "z_score"])


def _iqr_anomalies(
    metric_df: pd.DataFrame,
    group_cols: list[str],
    metric_col: str,
    multiplier: float,
) -> pd.DataFrame:
    results = []
    for _, group in metric_df.dropna(subset=[metric_col]).groupby(group_cols):
        if len(group) < MIN_GROUP_OBSERVATIONS:
            continue
        q1 = group[metric_col].quantile(0.25)
        q3 = group[metric_col].quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            continue
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        scored = group.copy()
        scored["observed_metric"] = scored[metric_col]
        scored["iqr_lower_bound"] = lower
        scored["iqr_upper_bound"] = upper
        results.append(scored[(scored[metric_col] < lower) | (scored[metric_col] > upper)])
    return _concat_or_empty(
        results,
        metric_df.columns.tolist() + ["observed_metric", "iqr_lower_bound", "iqr_upper_bound"],
    )


def _detections_from_anomalies(
    performance_df: pd.DataFrame,
    anomalies: pd.DataFrame,
    group_cols: list[str],
    rule_name: str,
    field_name: str,
    expected_condition: str,
    severity: str,
    explanation: str,
) -> pd.DataFrame:
    if anomalies.empty:
        return _detections_dataframe([])

    perf = performance_df.copy()
    perf["month_end_date"] = pd.to_datetime(perf["month_end_date"]).dt.strftime("%Y-%m-%d")
    merge_cols = group_cols + ["month_end_date"]
    merged = perf.merge(
        anomalies[merge_cols + ["observed_metric"]],
        on=merge_cols,
        how="inner",
    )

    rows = []
    for _, row in merged.iterrows():
        rows.append(
            {
                "detection_id": "",
                "rule_name": rule_name,
                "detection_family": "statistical_rule",
                "performance_id": row.get("performance_id", pd.NA),
                "account_id": row.get("account_id", pd.NA),
                "advisor_id": row.get("advisor_id", pd.NA),
                "branch_id": row.get("branch_id", pd.NA),
                "firm_crd_number": row.get("firm_crd_number", pd.NA),
                "month_end_date": row.get("month_end_date", pd.NA),
                "field_name": field_name,
                "observed_value": row.get("observed_metric", pd.NA),
                "expected_condition": expected_condition,
                "severity": severity,
                "explanation": explanation,
                "detected_at": DETECTED_AT,
            }
        )
    return _detections_dataframe(rows)


def _group_columns(group_level: str) -> list[str]:
    mapping = {
        "account": ["account_id"],
        "advisor": ["advisor_id"],
        "branch": ["branch_id"],
    }
    if group_level not in mapping:
        raise ValueError("group_level must be account, advisor, or branch")
    return mapping[group_level]


def _concat_or_empty(frames: list[pd.DataFrame], columns: list[str]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def _detections_dataframe(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=detection_result_columns())
