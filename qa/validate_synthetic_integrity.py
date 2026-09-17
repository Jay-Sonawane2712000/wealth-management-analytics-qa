"""Local integrity checks for clean baseline synthetic wealth data.

These checks protect the generated RAW.SYNTHETIC_* baseline before any later
phase intentionally injects errors for QA and anomaly-detection evaluation.
Validation failures are returned as rows instead of exceptions so reports and
tests can inspect all issues at once.
"""

from __future__ import annotations

import pandas as pd

ISSUE_COLUMNS = ["check_name", "severity", "issue_count", "details"]
REQUIRED_DATASET_COLUMNS = {
    "synthetic_branches": [
        "branch_id",
        "firm_crd_number",
        "branch_name",
        "branch_city",
        "branch_state",
        "branch_region",
        "opened_date",
        "is_active",
        "source_type",
        "generated_at",
    ],
    "synthetic_advisors": [
        "advisor_id",
        "firm_crd_number",
        "branch_id",
        "advisor_name",
        "advisor_tenure_years",
        "primary_client_segment",
        "is_active",
        "start_date",
        "source_type",
        "generated_at",
    ],
    "synthetic_accounts": [
        "account_id",
        "advisor_id",
        "firm_crd_number",
        "branch_id",
        "client_segment",
        "account_open_date",
        "account_status",
        "source_type",
        "generated_at",
    ],
    "synthetic_monthly_performance": [
        "performance_id",
        "account_id",
        "advisor_id",
        "firm_crd_number",
        "branch_id",
        "month_end_date",
        "beginning_aum",
        "ending_aum",
        "net_new_assets",
        "revenue",
        "fee_rate",
        "source_type",
        "generated_at",
    ],
}


def validate_required_columns(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Report missing required datasets or columns."""
    _ensure_dataset_mapping(datasets)
    issues = []
    for dataset_name, required_columns in REQUIRED_DATASET_COLUMNS.items():
        if dataset_name not in datasets:
            issues.append(
                _issue(
                    "required_columns",
                    1,
                    f"{dataset_name} dataset is missing",
                )
            )
            continue

        missing = [column for column in required_columns if column not in datasets[dataset_name].columns]
        if missing:
            issues.append(
                _issue(
                    "required_columns",
                    len(missing),
                    f"{dataset_name} is missing columns: {', '.join(missing)}",
                )
            )
    return _issues_dataframe(issues)


def validate_source_type(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Report rows where source_type is not synthetic."""
    _ensure_dataset_mapping(datasets)
    issues = []
    for dataset_name, dataset in datasets.items():
        if "source_type" not in dataset.columns:
            continue
        invalid_count = int((dataset["source_type"] != "synthetic").sum())
        if invalid_count:
            issues.append(
                _issue(
                    "source_type",
                    invalid_count,
                    f"{dataset_name} contains source_type values other than synthetic",
                )
            )
    return _issues_dataframe(issues)


def validate_branch_firm_links(branches: pd.DataFrame, firms: pd.DataFrame | None) -> pd.DataFrame:
    """Report branches that reference firm IDs outside the firm seed data."""
    if firms is None:
        return _issues_dataframe([])
    if "firm_crd_number" not in branches.columns or "firm_crd_number" not in firms.columns:
        return _issues_dataframe([])

    valid_firms = _as_string_set(firms["firm_crd_number"])
    invalid_count = int((~branches["firm_crd_number"].astype("string").isin(valid_firms)).sum())
    if invalid_count:
        return _issues_dataframe([
            _issue("branch_firm_links", invalid_count, "Branches reference missing firm_crd_number values")
        ])
    return _issues_dataframe([])


def validate_advisor_links(advisors: pd.DataFrame, branches: pd.DataFrame) -> pd.DataFrame:
    """Report advisors that reference missing branches."""
    if "branch_id" not in advisors.columns or "branch_id" not in branches.columns:
        return _issues_dataframe([])

    valid_branches = _as_string_set(branches["branch_id"])
    invalid_count = int((~advisors["branch_id"].astype("string").isin(valid_branches)).sum())
    if invalid_count:
        return _issues_dataframe([
            _issue("advisor_branch_links", invalid_count, "Advisors reference missing branch_id values")
        ])
    return _issues_dataframe([])


def validate_account_links(
    accounts: pd.DataFrame,
    advisors: pd.DataFrame,
    branches: pd.DataFrame,
) -> pd.DataFrame:
    """Report accounts that reference missing advisors or branches."""
    issues = []
    if "advisor_id" in accounts.columns and "advisor_id" in advisors.columns:
        invalid_advisors = int((~accounts["advisor_id"].astype("string").isin(_as_string_set(advisors["advisor_id"]))).sum())
        if invalid_advisors:
            issues.append(
                _issue("account_advisor_links", invalid_advisors, "Accounts reference missing advisor_id values")
            )

    if "branch_id" in accounts.columns and "branch_id" in branches.columns:
        invalid_branches = int((~accounts["branch_id"].astype("string").isin(_as_string_set(branches["branch_id"]))).sum())
        if invalid_branches:
            issues.append(
                _issue("account_branch_links", invalid_branches, "Accounts reference missing branch_id values")
            )

    return _issues_dataframe(issues)


def validate_performance_links(
    performance: pd.DataFrame,
    accounts: pd.DataFrame,
    advisors: pd.DataFrame,
    branches: pd.DataFrame,
) -> pd.DataFrame:
    """Report performance rows that reference missing parent records."""
    issues = []
    link_specs = [
        ("performance_account_links", "account_id", accounts, "Performance rows reference missing account_id values"),
        ("performance_advisor_links", "advisor_id", advisors, "Performance rows reference missing advisor_id values"),
        ("performance_branch_links", "branch_id", branches, "Performance rows reference missing branch_id values"),
    ]
    for check_name, column, parent_df, details in link_specs:
        if column not in performance.columns or column not in parent_df.columns:
            continue
        invalid_count = int((~performance[column].astype("string").isin(_as_string_set(parent_df[column]))).sum())
        if invalid_count:
            issues.append(_issue(check_name, invalid_count, details))

    return _issues_dataframe(issues)


def validate_financial_ranges(performance: pd.DataFrame) -> pd.DataFrame:
    """Report invalid clean-baseline performance values."""
    issues = []
    if "beginning_aum" in performance.columns:
        count = int((pd.to_numeric(performance["beginning_aum"], errors="coerce") < 0).sum())
        if count:
            issues.append(_issue("negative_beginning_aum", count, "Performance rows have negative beginning_aum"))

    if "ending_aum" in performance.columns:
        ending_aum = pd.to_numeric(performance["ending_aum"], errors="coerce")
        negative_count = int((ending_aum < 0).sum())
        missing_count = int(ending_aum.isna().sum())
        if negative_count:
            issues.append(_issue("negative_ending_aum", negative_count, "Performance rows have negative ending_aum"))
        if missing_count:
            issues.append(_issue("missing_ending_aum", missing_count, "Performance rows have missing ending_aum"))

    if "revenue" in performance.columns:
        count = int((pd.to_numeric(performance["revenue"], errors="coerce") < 0).sum())
        if count:
            issues.append(_issue("negative_revenue", count, "Performance rows have negative revenue"))

    if "fee_rate" in performance.columns:
        fee_rate = pd.to_numeric(performance["fee_rate"], errors="coerce")
        count = int(((fee_rate < 0.0025) | (fee_rate > 0.0150)).sum())
        if count:
            issues.append(_issue("fee_rate_range", count, "Performance rows have fee_rate outside 0.0025 to 0.0150"))

    return _issues_dataframe(issues)


def run_synthetic_integrity_checks(
    datasets: dict[str, pd.DataFrame],
    firms: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Run all synthetic clean-baseline integrity checks."""
    _ensure_dataset_mapping(datasets)
    issue_frames = [
        validate_required_columns(datasets),
        validate_source_type(datasets),
    ]

    if _has_required_datasets(datasets):
        branches = datasets["synthetic_branches"]
        advisors = datasets["synthetic_advisors"]
        accounts = datasets["synthetic_accounts"]
        performance = datasets["synthetic_monthly_performance"]
        issue_frames.extend(
            [
                validate_branch_firm_links(branches, firms),
                validate_advisor_links(advisors, branches),
                validate_account_links(accounts, advisors, branches),
                validate_performance_links(performance, accounts, advisors, branches),
                validate_financial_ranges(performance),
            ]
        )

    non_empty = [frame for frame in issue_frames if not frame.empty]
    if not non_empty:
        return _issues_dataframe([])
    return pd.concat(non_empty, ignore_index=True)[ISSUE_COLUMNS]


def _has_required_datasets(datasets: dict[str, pd.DataFrame]) -> bool:
    return all(name in datasets for name in REQUIRED_DATASET_COLUMNS)


def _ensure_dataset_mapping(datasets: dict[str, pd.DataFrame]) -> None:
    if not isinstance(datasets, dict):
        raise TypeError("datasets must be a dictionary of DataFrame objects")
    for name, dataset in datasets.items():
        if not isinstance(dataset, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame")


def _issue(check_name: str, issue_count: int, details: str, severity: str = "error") -> dict[str, object]:
    return {
        "check_name": check_name,
        "severity": severity,
        "issue_count": issue_count,
        "details": details,
    }


def _issues_dataframe(issues: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(issues, columns=ISSUE_COLUMNS)


def _as_string_set(series: pd.Series) -> set[str]:
    return set(series.astype("string").dropna())
