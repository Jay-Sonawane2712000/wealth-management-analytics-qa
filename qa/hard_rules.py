"""Deterministic hard-rule QA checks for financial reporting data.

Hard rules catch obvious reporting issues such as negative values, invalid fee
rates, duplicate account-month records, closed-account revenue, missing parent
references, and null key fields. Statistical anomaly detection and scoring
against ground truth are intentionally left for later phases.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "qa" / "detections"
DETECTION_COLUMNS = [
    "detection_id",
    "rule_name",
    "detection_family",
    "performance_id",
    "account_id",
    "advisor_id",
    "branch_id",
    "firm_crd_number",
    "month_end_date",
    "field_name",
    "observed_value",
    "expected_condition",
    "severity",
    "explanation",
    "detected_at",
]
HARD_RULE_CATEGORIES = ("completeness", "validity", "relationship", "duplicate")
DETECTED_AT = "2026-01-20T00:00:00"


def available_rule_categories() -> tuple[str, ...]:
    """Return hard-rule category names."""
    return HARD_RULE_CATEGORIES


def detection_result_columns() -> list[str]:
    """Return the canonical detection result schema."""
    return DETECTION_COLUMNS.copy()


def make_detection_result(
    rule_name: str,
    row: pd.Series,
    field_name: str,
    observed_value: object,
    expected_condition: str,
    severity: str,
    explanation: str,
    detection_id: str = "",
) -> dict[str, object]:
    """Build one hard-rule detection result row."""
    return {
        "detection_id": detection_id,
        "rule_name": rule_name,
        "detection_family": "hard_rule",
        "performance_id": row.get("performance_id", pd.NA),
        "account_id": row.get("account_id", pd.NA),
        "advisor_id": row.get("advisor_id", pd.NA),
        "branch_id": row.get("branch_id", pd.NA),
        "firm_crd_number": row.get("firm_crd_number", pd.NA),
        "month_end_date": row.get("month_end_date", pd.NA),
        "field_name": field_name,
        "observed_value": observed_value,
        "expected_condition": expected_condition,
        "severity": severity,
        "explanation": explanation,
        "detected_at": DETECTED_AT,
    }


def detect_negative_ending_aum(performance_df: pd.DataFrame) -> pd.DataFrame:
    """Detect rows where ending_aum is below zero."""
    rows = []
    ending_aum = pd.to_numeric(performance_df["ending_aum"], errors="coerce")
    for _, row in performance_df.loc[ending_aum < 0].iterrows():
        rows.append(
            make_detection_result(
                "negative_ending_aum",
                row,
                "ending_aum",
                row["ending_aum"],
                "ending_aum >= 0",
                "high",
                "Ending AUM is negative.",
            )
        )
    return _detections_dataframe(rows)


def detect_negative_revenue(performance_df: pd.DataFrame) -> pd.DataFrame:
    """Detect rows where revenue is below zero."""
    rows = []
    revenue = pd.to_numeric(performance_df["revenue"], errors="coerce")
    for _, row in performance_df.loc[revenue < 0].iterrows():
        rows.append(
            make_detection_result(
                "negative_revenue",
                row,
                "revenue",
                row["revenue"],
                "revenue >= 0",
                "high",
                "Revenue is negative.",
            )
        )
    return _detections_dataframe(rows)


def detect_invalid_fee_rates(performance_df: pd.DataFrame) -> pd.DataFrame:
    """Detect fee rates outside the clean baseline range."""
    rows = []
    fee_rate = pd.to_numeric(performance_df["fee_rate"], errors="coerce")
    high_rows = performance_df.loc[fee_rate > 0.0150]
    low_rows = performance_df.loc[fee_rate < 0.0025]

    for _, row in high_rows.iterrows():
        rows.append(
            make_detection_result(
                "invalid_fee_rate_high",
                row,
                "fee_rate",
                row["fee_rate"],
                "fee_rate <= 0.0150",
                "high",
                "Fee rate is above the expected advisory range.",
            )
        )

    for _, row in low_rows.iterrows():
        rows.append(
            make_detection_result(
                "invalid_fee_rate_low",
                row,
                "fee_rate",
                row["fee_rate"],
                "fee_rate >= 0.0025",
                "medium",
                "Fee rate is below the expected advisory range.",
            )
        )

    return _detections_dataframe(rows)


def detect_duplicate_account_month(performance_df: pd.DataFrame) -> pd.DataFrame:
    """Detect duplicate account_id plus month_end_date combinations."""
    rows = []
    duplicate_mask = performance_df.duplicated(["account_id", "month_end_date"], keep=False)
    for _, row in performance_df.loc[duplicate_mask].iterrows():
        rows.append(
            make_detection_result(
                "duplicate_account_month",
                row,
                "account_id,month_end_date",
                f"{row.get('account_id')}|{row.get('month_end_date')}",
                "one row per account_id and month_end_date",
                "high",
                "Multiple performance rows exist for the same account-month.",
            )
        )
    return _detections_dataframe(rows)


def detect_revenue_on_closed_accounts(
    performance_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
) -> pd.DataFrame:
    """Detect positive revenue on accounts marked closed."""
    rows = []
    closed_accounts = set(
        accounts_df.loc[accounts_df["account_status"] == "closed", "account_id"].astype("string")
    )
    revenue = pd.to_numeric(performance_df["revenue"], errors="coerce")
    mask = performance_df["account_id"].astype("string").isin(closed_accounts) & (revenue > 0)

    for _, row in performance_df.loc[mask].iterrows():
        rows.append(
            make_detection_result(
                "revenue_on_closed_account",
                row,
                "revenue",
                row["revenue"],
                "revenue = 0 when account_status = closed",
                "medium",
                "Closed account has positive revenue.",
            )
        )
    return _detections_dataframe(rows)


def detect_missing_references(
    performance_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
    advisors_df: pd.DataFrame,
    branches_df: pd.DataFrame,
) -> pd.DataFrame:
    """Detect missing account, advisor, and branch parent references."""
    rows = []
    reference_specs = [
        (
            "missing_account_reference",
            "account_id",
            set(accounts_df["account_id"].astype("string")),
            "account_id exists in synthetic_accounts",
            "Performance row references a missing account.",
        ),
        (
            "missing_advisor_reference",
            "advisor_id",
            set(advisors_df["advisor_id"].astype("string")),
            "advisor_id exists in synthetic_advisors",
            "Performance row references a missing advisor.",
        ),
        (
            "missing_branch_reference",
            "branch_id",
            set(branches_df["branch_id"].astype("string")),
            "branch_id exists in synthetic_branches",
            "Performance row references a missing branch.",
        ),
    ]

    for rule_name, field_name, valid_values, expected_condition, explanation in reference_specs:
        values = performance_df[field_name].astype("string")
        mask = values.notna() & ~values.isin(valid_values)
        for _, row in performance_df.loc[mask].iterrows():
            rows.append(
                make_detection_result(
                    rule_name,
                    row,
                    field_name,
                    row[field_name],
                    expected_condition,
                    "high",
                    explanation,
                )
            )

    return _detections_dataframe(rows)


def detect_null_key_fields(performance_df: pd.DataFrame) -> pd.DataFrame:
    """Detect missing values in required key fields."""
    rows = []
    key_fields = [
        "performance_id",
        "account_id",
        "advisor_id",
        "branch_id",
        "firm_crd_number",
        "month_end_date",
    ]
    for _, row in performance_df.iterrows():
        missing_fields = [field for field in key_fields if pd.isna(row.get(field))]
        if missing_fields:
            rows.append(
                make_detection_result(
                    "null_key_fields",
                    row,
                    ",".join(missing_fields),
                    "NULL",
                    "key fields are not null",
                    "high",
                    f"Missing required key field(s): {', '.join(missing_fields)}.",
                )
            )
    return _detections_dataframe(rows)


def run_hard_rule_detection(
    performance_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
    advisors_df: pd.DataFrame,
    branches_df: pd.DataFrame,
) -> pd.DataFrame:
    """Run all deterministic hard-rule checks."""
    frames = [
        detect_negative_ending_aum(performance_df),
        detect_negative_revenue(performance_df),
        detect_invalid_fee_rates(performance_df),
        detect_duplicate_account_month(performance_df),
        detect_revenue_on_closed_accounts(performance_df, accounts_df),
        detect_missing_references(performance_df, accounts_df, advisors_df, branches_df),
        detect_null_key_fields(performance_df),
    ]
    non_empty = [frame for frame in frames if not frame.empty]
    if not non_empty:
        return _detections_dataframe([])

    detections = pd.concat(non_empty, ignore_index=True)[DETECTION_COLUMNS]
    detections["detection_id"] = [
        f"HARD-{index:06d}" for index in range(1, len(detections) + 1)
    ]
    return detections


def save_detection_results(
    detection_results_df: pd.DataFrame,
    output_dir: str | Path | None = None,
) -> Path:
    """Save hard-rule detection results to CSV."""
    path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)
    output_path = path / "hard_rule_detection_results.csv"
    detection_results_df.to_csv(output_path, index=False)
    return output_path


def _detections_dataframe(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=DETECTION_COLUMNS)
