"""Small pandas helpers for checking baseline KPI formulas locally."""

from __future__ import annotations

import pandas as pd


def calculate_advisor_monthly_kpis(performance: pd.DataFrame) -> pd.DataFrame:
    """Calculate advisor-level monthly KPI math from performance records."""
    grouped = _group_performance(
        performance,
        ["month_end_date", "firm_crd_number", "branch_id", "advisor_id"],
    )
    grouped["revenue_per_account"] = grouped["revenue"] / grouped["account_count"].replace(0, pd.NA)
    return grouped


def calculate_branch_monthly_kpis(performance: pd.DataFrame) -> pd.DataFrame:
    """Calculate branch-level monthly KPI math from performance records."""
    grouped = _group_performance(
        performance,
        ["month_end_date", "firm_crd_number", "branch_id"],
    )
    advisor_counts = (
        performance.groupby(["month_end_date", "firm_crd_number", "branch_id"])["advisor_id"]
        .nunique()
        .reset_index(name="advisor_count")
    )
    grouped = grouped.merge(advisor_counts, on=["month_end_date", "firm_crd_number", "branch_id"])
    grouped["revenue_per_advisor"] = grouped["revenue"] / grouped["advisor_count"].replace(0, pd.NA)
    return grouped


def calculate_firm_monthly_kpis(performance: pd.DataFrame) -> pd.DataFrame:
    """Calculate firm-level monthly KPI math from performance records."""
    return _group_performance(performance, ["month_end_date", "firm_crd_number"])


def _group_performance(performance: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    grouped = (
        performance.groupby(group_columns, as_index=False)
        .agg(
            account_count=("account_id", "nunique"),
            beginning_aum=("beginning_aum", "sum"),
            ending_aum=("ending_aum", "sum"),
            net_new_assets=("net_new_assets", "sum"),
            revenue=("revenue", "sum"),
            avg_fee_rate=("fee_rate", "mean"),
        )
    )
    grouped["aum_growth_rate"] = (
        (grouped["ending_aum"] - grouped["beginning_aum"])
        / grouped["beginning_aum"].replace(0, pd.NA)
    )
    return grouped
