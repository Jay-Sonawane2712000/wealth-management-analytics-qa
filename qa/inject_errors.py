"""Seeded-error injection for measured financial reporting QA.

This module intentionally corrupts a copy of clean synthetic monthly
performance data and creates a labeled ground-truth answer key. The clean input
data is never mutated in place. Later phases will use this answer key to
measure hard-rule and statistical anomaly detection performance.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

GROUND_TRUTH_TABLE = "QA.GROUND_TRUTH_INJECTED_ERRORS"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "synthetic_corrupted"
GROUND_TRUTH_COLUMNS = [
    "error_id",
    "performance_id",
    "account_id",
    "advisor_id",
    "branch_id",
    "firm_crd_number",
    "month_end_date",
    "error_type",
    "field_name",
    "original_value",
    "corrupted_value",
    "severity",
    "detection_family",
    "explanation",
    "injected_at",
]
EXPECTED_ERROR_TYPES = [
    "negative_ending_aum",
    "negative_revenue",
    "invalid_fee_rate_high",
    "duplicate_account_month",
    "revenue_on_closed_account",
    "extreme_aum_jump_positive",
    "extreme_aum_jump_negative",
    "extreme_revenue_spike",
]


def planned_ground_truth_table() -> str:
    """Return the planned Snowflake table for injected-error ground truth."""
    return GROUND_TRUTH_TABLE


def default_error_plan() -> dict[str, int]:
    """Return a controlled default count for each seeded error type."""
    return {
        "negative_ending_aum": 5,
        "negative_revenue": 5,
        "invalid_fee_rate_high": 5,
        "duplicate_account_month": 5,
        "revenue_on_closed_account": 5,
        "extreme_aum_jump_positive": 5,
        "extreme_aum_jump_negative": 5,
        "extreme_revenue_spike": 5,
    }


def select_candidate_rows(
    performance_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
    error_type: str,
    count: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Select candidate performance rows for one error type."""
    if count <= 0:
        return performance_df.head(0).copy()

    candidates = performance_df.copy()
    if error_type == "revenue_on_closed_account":
        closed_accounts = set(
            accounts_df.loc[accounts_df["account_status"] == "closed", "account_id"].astype(str)
        )
        candidates = candidates[candidates["account_id"].astype(str).isin(closed_accounts)]
    elif error_type in {"negative_ending_aum", "extreme_aum_jump_positive", "extreme_aum_jump_negative"}:
        candidates = candidates[pd.to_numeric(candidates["beginning_aum"], errors="coerce") > 0]
    elif error_type == "extreme_revenue_spike":
        candidates = candidates[pd.to_numeric(candidates["revenue"], errors="coerce") >= 0]

    if candidates.empty:
        return candidates.copy()

    sample_size = min(count, len(candidates))
    selected_positions = rng.choice(candidates.index.to_numpy(), size=sample_size, replace=False)
    return candidates.loc[selected_positions].copy()


def inject_negative_ending_aum(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> dict[str, object]:
    """Set ending_aum below zero and return a ground-truth row."""
    original = performance_df.at[row.name, "ending_aum"]
    corrupted = -abs(float(original if pd.notna(original) else 1.0))
    if corrupted == 0:
        corrupted = -1.0
    performance_df.at[row.name, "ending_aum"] = round(corrupted, 2)
    performance_df.at[row.name, "source_type"] = "synthetic_corrupted"
    return _ground_truth_row(
        row,
        error_number,
        "negative_ending_aum",
        "ending_aum",
        original,
        performance_df.at[row.name, "ending_aum"],
        "high",
        "hard_rule",
        "Ending AUM was set below zero, which is impossible for clean reporting data.",
        injected_at,
    )


def inject_negative_revenue(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> dict[str, object]:
    """Set revenue below zero and return a ground-truth row."""
    original = performance_df.at[row.name, "revenue"]
    corrupted = -abs(float(original if pd.notna(original) else 1.0))
    if corrupted == 0:
        corrupted = -1.0
    performance_df.at[row.name, "revenue"] = round(corrupted, 2)
    performance_df.at[row.name, "source_type"] = "synthetic_corrupted"
    return _ground_truth_row(
        row,
        error_number,
        "negative_revenue",
        "revenue",
        original,
        performance_df.at[row.name, "revenue"],
        "high",
        "hard_rule",
        "Revenue was set below zero, which should be rejected by deterministic QA rules.",
        injected_at,
    )


def inject_invalid_fee_rate_high(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> dict[str, object]:
    """Set fee_rate above the expected advisory range."""
    original = performance_df.at[row.name, "fee_rate"]
    performance_df.at[row.name, "fee_rate"] = 0.035
    performance_df.at[row.name, "source_type"] = "synthetic_corrupted"
    return _ground_truth_row(
        row,
        error_number,
        "invalid_fee_rate_high",
        "fee_rate",
        original,
        0.035,
        "high",
        "hard_rule",
        "Fee rate was set above the expected clean baseline range.",
        injected_at,
    )


def inject_duplicate_account_month(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Duplicate an account-month row with a new performance_id."""
    duplicate = row.copy()
    duplicate["performance_id"] = f"DUP-{row['performance_id']}"
    duplicate["source_type"] = "synthetic_corrupted"
    updated_performance = pd.concat([performance_df, duplicate.to_frame().T], ignore_index=True)
    truth_row = _ground_truth_row(
        duplicate,
        error_number,
        "duplicate_account_month",
        "performance_id",
        row["performance_id"],
        duplicate["performance_id"],
        "high",
        "hard_rule",
        "A second row was created for the same account_id and month_end_date.",
        injected_at,
    )
    return updated_performance, truth_row


def inject_revenue_on_closed_account(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> dict[str, object]:
    """Set positive revenue on a closed account performance row."""
    original = performance_df.at[row.name, "revenue"]
    new_revenue = max(float(original if pd.notna(original) else 0.0) + 500.0, 500.0)
    performance_df.at[row.name, "revenue"] = round(new_revenue, 2)
    performance_df.at[row.name, "source_type"] = "synthetic_corrupted"
    return _ground_truth_row(
        row,
        error_number,
        "revenue_on_closed_account",
        "revenue",
        original,
        performance_df.at[row.name, "revenue"],
        "medium",
        "hard_rule",
        "Revenue was forced positive for a closed account row.",
        injected_at,
    )


def inject_extreme_aum_jump_positive(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> dict[str, object]:
    """Create an implausible positive AUM jump without matching net new assets."""
    original = performance_df.at[row.name, "ending_aum"]
    beginning = float(performance_df.at[row.name, "beginning_aum"])
    performance_df.at[row.name, "ending_aum"] = round(beginning * 1.60, 2)
    performance_df.at[row.name, "net_new_assets"] = 0.0
    performance_df.at[row.name, "source_type"] = "synthetic_corrupted"
    return _ground_truth_row(
        row,
        error_number,
        "extreme_aum_jump_positive",
        "ending_aum",
        original,
        performance_df.at[row.name, "ending_aum"],
        "medium",
        "statistical_rule",
        "Ending AUM was increased by roughly 60% without corresponding net new assets.",
        injected_at,
    )


def inject_extreme_aum_jump_negative(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> dict[str, object]:
    """Create an implausible negative AUM drop without matching net new assets."""
    original = performance_df.at[row.name, "ending_aum"]
    beginning = float(performance_df.at[row.name, "beginning_aum"])
    performance_df.at[row.name, "ending_aum"] = round(beginning * 0.50, 2)
    performance_df.at[row.name, "net_new_assets"] = 0.0
    performance_df.at[row.name, "source_type"] = "synthetic_corrupted"
    return _ground_truth_row(
        row,
        error_number,
        "extreme_aum_jump_negative",
        "ending_aum",
        original,
        performance_df.at[row.name, "ending_aum"],
        "medium",
        "statistical_rule",
        "Ending AUM was reduced by roughly 50% without corresponding net new assets.",
        injected_at,
    )


def inject_extreme_revenue_spike(
    performance_df: pd.DataFrame,
    row: pd.Series,
    error_number: int,
    injected_at: str,
) -> dict[str, object]:
    """Create an unusually high revenue month."""
    original = performance_df.at[row.name, "revenue"]
    beginning = float(performance_df.at[row.name, "beginning_aum"])
    performance_df.at[row.name, "revenue"] = round(max(float(original) * 8, beginning * 0.035 / 12), 2)
    performance_df.at[row.name, "source_type"] = "synthetic_corrupted"
    return _ground_truth_row(
        row,
        error_number,
        "extreme_revenue_spike",
        "revenue",
        original,
        performance_df.at[row.name, "revenue"],
        "medium",
        "statistical_rule",
        "Revenue was spiked well above the expected surrounding account/advisor pattern.",
        injected_at,
    )


def inject_seeded_errors(
    datasets: dict[str, pd.DataFrame],
    error_plan: dict[str, int] | None = None,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inject seeded errors into a copy of synthetic monthly performance data."""
    _validate_input_datasets(datasets)
    plan = default_error_plan() if error_plan is None else error_plan
    rng = np.random.default_rng(seed)
    injected_at = _injected_timestamp(seed)

    accounts = datasets["synthetic_accounts"]
    original_performance = datasets["synthetic_monthly_performance"]
    corrupted = original_performance.copy(deep=True).reset_index(drop=True)
    ground_truth_rows: list[dict[str, object]] = []
    used_performance_ids: set[str] = set()

    for error_type in EXPECTED_ERROR_TYPES:
        count = int(plan.get(error_type, 0))
        candidates = select_candidate_rows(corrupted, accounts, error_type, count * 3, rng)
        candidates = candidates[
            ~candidates["performance_id"].astype(str).isin(used_performance_ids)
        ].head(count)

        for _, candidate in candidates.iterrows():
            row_index = corrupted.index[corrupted["performance_id"] == candidate["performance_id"]][0]
            row = corrupted.loc[row_index].copy()
            row.name = row_index
            error_number = len(ground_truth_rows) + 1

            if error_type == "negative_ending_aum":
                truth = inject_negative_ending_aum(corrupted, row, error_number, injected_at)
            elif error_type == "negative_revenue":
                truth = inject_negative_revenue(corrupted, row, error_number, injected_at)
            elif error_type == "invalid_fee_rate_high":
                truth = inject_invalid_fee_rate_high(corrupted, row, error_number, injected_at)
            elif error_type == "duplicate_account_month":
                corrupted, truth = inject_duplicate_account_month(corrupted, row, error_number, injected_at)
            elif error_type == "revenue_on_closed_account":
                truth = inject_revenue_on_closed_account(corrupted, row, error_number, injected_at)
            elif error_type == "extreme_aum_jump_positive":
                truth = inject_extreme_aum_jump_positive(corrupted, row, error_number, injected_at)
            elif error_type == "extreme_aum_jump_negative":
                truth = inject_extreme_aum_jump_negative(corrupted, row, error_number, injected_at)
            elif error_type == "extreme_revenue_spike":
                truth = inject_extreme_revenue_spike(corrupted, row, error_number, injected_at)
            else:
                raise ValueError(f"Unsupported error_type: {error_type}")

            ground_truth_rows.append(truth)
            used_performance_ids.add(str(candidate["performance_id"]))

    ground_truth = pd.DataFrame(ground_truth_rows, columns=GROUND_TRUTH_COLUMNS)
    return corrupted.reset_index(drop=True), ground_truth


def save_injected_error_outputs(
    corrupted_performance_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Save corrupted performance and ground-truth answer key CSVs."""
    path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)

    outputs = {
        "synthetic_monthly_performance_corrupted": path / "synthetic_monthly_performance_corrupted.csv",
        "ground_truth_injected_errors": path / "ground_truth_injected_errors.csv",
    }
    corrupted_performance_df.to_csv(outputs["synthetic_monthly_performance_corrupted"], index=False)
    ground_truth_df.to_csv(outputs["ground_truth_injected_errors"], index=False)
    return outputs


def _validate_input_datasets(datasets: dict[str, pd.DataFrame]) -> None:
    required = {
        "synthetic_accounts",
        "synthetic_advisors",
        "synthetic_branches",
        "synthetic_monthly_performance",
    }
    missing = required - set(datasets)
    if missing:
        raise ValueError(f"Missing synthetic datasets: {', '.join(sorted(missing))}")


def _ground_truth_row(
    row: pd.Series,
    error_number: int,
    error_type: str,
    field_name: str,
    original_value: object,
    corrupted_value: object,
    severity: str,
    detection_family: str,
    explanation: str,
    injected_at: str,
) -> dict[str, object]:
    return {
        "error_id": f"ERR-{error_number:05d}",
        "performance_id": row["performance_id"],
        "account_id": row["account_id"],
        "advisor_id": row["advisor_id"],
        "branch_id": row["branch_id"],
        "firm_crd_number": row["firm_crd_number"],
        "month_end_date": row["month_end_date"],
        "error_type": error_type,
        "field_name": field_name,
        "original_value": original_value,
        "corrupted_value": corrupted_value,
        "severity": severity,
        "detection_family": detection_family,
        "explanation": explanation,
        "injected_at": injected_at,
    }


def _injected_timestamp(seed: int) -> str:
    return (pd.Timestamp("2026-01-15T00:00:00") + pd.Timedelta(seconds=seed)).isoformat()
