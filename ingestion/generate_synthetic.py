"""Synthetic wealth-management data generator.

This module creates private-style branch, advisor, account, and monthly
performance data for future RAW.SYNTHETIC_* tables. It uses real/public firm
seed data when a normalized SEC ADV file is available, but every generated row
in this module is labeled as synthetic.

The generated data is intentionally clean baseline data. Later QA phases will
inject known errors into this baseline so anomaly detection can be evaluated.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ingestion.fetch_sec_adv import build_sec_adv_firms_dataset

SYNTHETIC_TABLE_PREFIX = "RAW.SYNTHETIC_"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIRM_SEED_PATH = PROJECT_ROOT / "data" / "processed" / "sec_adv_firms_normalized.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "synthetic"
CLIENT_SEGMENTS = ("emerging_affluent", "affluent", "high_net_worth", "institutional")
BRANCH_REGIONS = {
    "CA": "West",
    "WA": "West",
    "OR": "West",
    "AZ": "West",
    "CO": "Mountain",
    "TX": "South",
    "NC": "Southeast",
    "GA": "Southeast",
    "FL": "Southeast",
    "IL": "Midwest",
    "MN": "Midwest",
    "OH": "Midwest",
    "NY": "Northeast",
    "MA": "Northeast",
    "PA": "Northeast",
}
BRANCH_COLUMNS = [
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
]
ADVISOR_COLUMNS = [
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
]
ACCOUNT_COLUMNS = [
    "account_id",
    "advisor_id",
    "firm_crd_number",
    "branch_id",
    "client_segment",
    "account_open_date",
    "account_status",
    "source_type",
    "generated_at",
]
PERFORMANCE_COLUMNS = [
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
]


def planned_table_prefix() -> str:
    """Return the planned prefix for synthetic raw Snowflake tables."""
    return SYNTHETIC_TABLE_PREFIX


def load_firm_seed_data(path: str | Path | None = None, max_firms: int = 30) -> pd.DataFrame:
    """Load firm seed data from normalized SEC ADV output or a fallback sample."""
    seed_path = Path(path) if path is not None else DEFAULT_FIRM_SEED_PATH

    if seed_path.exists():
        firms = pd.read_csv(seed_path, dtype={"firm_crd_number": "string"})
    else:
        firms = build_sec_adv_firms_dataset(allow_sample_fallback=True)

    required = ["firm_crd_number", "firm_name", "main_office_city", "main_office_state"]
    missing = [column for column in required if column not in firms.columns]
    if missing:
        raise ValueError(f"Firm seed data is missing required columns: {', '.join(missing)}")

    firms = firms[required].dropna(subset=["firm_crd_number", "firm_name"]).copy()
    firms["firm_crd_number"] = firms["firm_crd_number"].astype("string")
    return firms.head(max_firms).reset_index(drop=True)


def generate_branches(firms_df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate 2 to 5 synthetic branches for each firm."""
    rng = np.random.default_rng(seed)
    rows = []
    branch_number = 1
    generated_at = _generated_timestamp(seed)

    for firm in firms_df.itertuples(index=False):
        branch_count = int(rng.integers(2, 6))
        for local_number in range(1, branch_count + 1):
            state = _choose_state(rng, getattr(firm, "main_office_state", None))
            city = _choose_city(rng, getattr(firm, "main_office_city", None), state)
            rows.append(
                {
                    "branch_id": f"BR-{branch_number:05d}",
                    "firm_crd_number": str(firm.firm_crd_number),
                    "branch_name": f"{firm.firm_name} - {city} {local_number}",
                    "branch_city": city,
                    "branch_state": state,
                    "branch_region": BRANCH_REGIONS.get(state, "Other"),
                    "opened_date": _random_past_date(rng, max_years=18),
                    "is_active": bool(rng.random() > 0.06),
                    "source_type": "synthetic",
                    "generated_at": generated_at,
                }
            )
            branch_number += 1

    return pd.DataFrame(rows, columns=BRANCH_COLUMNS)


def generate_advisors(branches_df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate 3 to 8 synthetic advisors for each branch."""
    rng = np.random.default_rng(seed + 1)
    rows = []
    advisor_number = 1
    generated_at = _generated_timestamp(seed)

    for branch in branches_df.itertuples(index=False):
        advisor_count = int(rng.integers(3, 9))
        for _ in range(advisor_count):
            tenure = int(rng.integers(0, 31))
            rows.append(
                {
                    "advisor_id": f"ADV-{advisor_number:06d}",
                    "firm_crd_number": str(branch.firm_crd_number),
                    "branch_id": branch.branch_id,
                    "advisor_name": _advisor_name(rng, advisor_number),
                    "advisor_tenure_years": tenure,
                    "primary_client_segment": str(rng.choice(CLIENT_SEGMENTS, p=[0.28, 0.34, 0.28, 0.10])),
                    "is_active": bool(rng.random() > 0.04),
                    "start_date": _date_years_ago(tenure),
                    "source_type": "synthetic",
                    "generated_at": generated_at,
                }
            )
            advisor_number += 1

    return pd.DataFrame(rows, columns=ADVISOR_COLUMNS)


def generate_accounts(advisors_df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate 15 to 60 synthetic accounts for each advisor."""
    rng = np.random.default_rng(seed + 2)
    rows = []
    account_number = 1
    generated_at = _generated_timestamp(seed)

    for advisor in advisors_df.itertuples(index=False):
        account_count = int(rng.integers(15, 61))
        for _ in range(account_count):
            segment = _account_segment(rng, advisor.primary_client_segment)
            rows.append(
                {
                    "account_id": f"ACCT-{account_number:08d}",
                    "advisor_id": advisor.advisor_id,
                    "firm_crd_number": str(advisor.firm_crd_number),
                    "branch_id": advisor.branch_id,
                    "client_segment": segment,
                    "account_open_date": _random_past_date(rng, max_years=12),
                    "account_status": str(rng.choice(["active", "closed"], p=[0.93, 0.07])),
                    "source_type": "synthetic",
                    "generated_at": generated_at,
                }
            )
            account_number += 1

    return pd.DataFrame(rows, columns=ACCOUNT_COLUMNS)


def generate_monthly_performance(
    accounts_df: pd.DataFrame,
    months: int = 12,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate clean monthly performance records for each account."""
    if months < 1:
        raise ValueError("months must be at least 1")

    rng = np.random.default_rng(seed + 3)
    rows = []
    performance_number = 1
    generated_at = _generated_timestamp(seed)
    month_ends = _month_end_dates(months)

    for account in accounts_df.itertuples(index=False):
        beginning_aum = _initial_aum(rng, account.client_segment)
        fee_rate = _fee_rate(rng, account.client_segment)

        for month_end in month_ends:
            monthly_return = rng.normal(0.006, 0.028)
            if account.account_status == "closed" and month_end == month_ends[-1]:
                net_new_assets = -beginning_aum
            else:
                net_new_assets = _net_new_assets(rng, beginning_aum, account.client_segment)

            ending_aum = max(0.0, beginning_aum * (1 + monthly_return) + net_new_assets)
            average_aum = (beginning_aum + ending_aum) / 2
            revenue = max(0.0, average_aum * fee_rate / 12)

            rows.append(
                {
                    "performance_id": f"PERF-{performance_number:010d}",
                    "account_id": account.account_id,
                    "advisor_id": account.advisor_id,
                    "firm_crd_number": str(account.firm_crd_number),
                    "branch_id": account.branch_id,
                    "month_end_date": month_end,
                    "beginning_aum": round(beginning_aum, 2),
                    "ending_aum": round(ending_aum, 2),
                    "net_new_assets": round(net_new_assets, 2),
                    "revenue": round(revenue, 2),
                    "fee_rate": round(fee_rate, 4),
                    "source_type": "synthetic",
                    "generated_at": generated_at,
                }
            )

            beginning_aum = ending_aum
            performance_number += 1

    return pd.DataFrame(rows, columns=PERFORMANCE_COLUMNS)


def generate_all_synthetic_data(
    output_dir: str | Path | None = None,
    seed: int = 42,
    months: int = 12,
    validate: bool = True,
) -> dict[str, pd.DataFrame]:
    """Generate all synthetic wealth-management datasets and optionally save them."""
    firms = load_firm_seed_data(max_firms=30)
    branches = generate_branches(firms, seed=seed)
    advisors = generate_advisors(branches, seed=seed)
    accounts = generate_accounts(advisors, seed=seed)
    monthly_performance = generate_monthly_performance(accounts, months=months, seed=seed)

    datasets = {
        "synthetic_branches": branches,
        "synthetic_advisors": advisors,
        "synthetic_accounts": accounts,
        "synthetic_monthly_performance": monthly_performance,
    }

    if validate:
        from qa.validate_synthetic_integrity import run_synthetic_integrity_checks

        issues = run_synthetic_integrity_checks(datasets, firms=firms)
        if not issues.empty:
            issue_summary = "; ".join(
                f"{row.check_name}={row.issue_count}" for row in issues.itertuples(index=False)
            )
            raise ValueError(
                "Synthetic baseline integrity checks failed. "
                f"Issue counts: {issue_summary}. "
                "Use validate=False only for intentionally corrupted QA datasets."
            )

    if output_dir is not None:
        save_synthetic_datasets(datasets, output_dir)

    return datasets


def save_synthetic_datasets(
    datasets: dict[str, pd.DataFrame],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Save synthetic datasets as CSV files and return their paths."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_paths = {}
    for name, df in datasets.items():
        file_path = output_path / f"{name}.csv"
        df.to_csv(file_path, index=False)
        saved_paths[name] = file_path

    return saved_paths


def _generated_timestamp(seed: int) -> str:
    """Return a deterministic timestamp for reproducible generated datasets."""
    return (pd.Timestamp("2026-01-01T00:00:00") + pd.Timedelta(seconds=seed)).isoformat()


def _choose_state(rng: np.random.Generator, seed_state: object) -> str:
    states = ["CA", "TX", "NY", "FL", "IL", "MA", "CO", "AZ", "NC", "WA"]
    if pd.notna(seed_state) and str(seed_state).strip():
        if rng.random() < 0.65:
            return str(seed_state).strip().upper()
    return str(rng.choice(states))


def _choose_city(rng: np.random.Generator, seed_city: object, state: str) -> str:
    cities_by_state = {
        "CA": ["San Francisco", "Los Angeles", "San Diego"],
        "TX": ["Austin", "Dallas", "Houston"],
        "NY": ["New York", "Albany", "White Plains"],
        "FL": ["Miami", "Tampa", "Orlando"],
        "IL": ["Chicago", "Naperville", "Oak Brook"],
        "MA": ["Boston", "Cambridge", "Waltham"],
        "CO": ["Denver", "Boulder", "Colorado Springs"],
        "AZ": ["Phoenix", "Scottsdale", "Tempe"],
        "NC": ["Charlotte", "Raleigh", "Durham"],
        "WA": ["Seattle", "Bellevue", "Tacoma"],
    }
    if pd.notna(seed_city) and str(seed_city).strip() and rng.random() < 0.60:
        return str(seed_city).strip()
    return str(rng.choice(cities_by_state.get(state, ["Regional Office"])))


def _random_past_date(rng: np.random.Generator, max_years: int) -> str:
    days_back = int(rng.integers(90, max_years * 365))
    return (pd.Timestamp("2026-08-31") - pd.Timedelta(days=days_back)).date().isoformat()


def _date_years_ago(years: int) -> str:
    days = max(30, int(years * 365.25))
    return (pd.Timestamp("2026-08-31") - pd.Timedelta(days=days)).date().isoformat()


def _advisor_name(rng: np.random.Generator, advisor_number: int) -> str:
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Cameron"]
    last_names = ["Parker", "Lee", "Morgan", "Patel", "Rivera", "Chen", "Brooks", "Campbell"]
    return f"{rng.choice(first_names)} {rng.choice(last_names)} {advisor_number}"


def _account_segment(rng: np.random.Generator, advisor_segment: str) -> str:
    if rng.random() < 0.58:
        return advisor_segment
    return str(rng.choice(CLIENT_SEGMENTS, p=[0.28, 0.34, 0.28, 0.10]))


def _initial_aum(rng: np.random.Generator, segment: str) -> float:
    ranges = {
        "emerging_affluent": (75_000, 350_000),
        "affluent": (350_000, 1_500_000),
        "high_net_worth": (1_500_000, 8_000_000),
        "institutional": (8_000_000, 35_000_000),
    }
    low, high = ranges.get(segment, (250_000, 1_000_000))
    return float(rng.uniform(low, high))


def _fee_rate(rng: np.random.Generator, segment: str) -> float:
    ranges = {
        "emerging_affluent": (0.0090, 0.0150),
        "affluent": (0.0070, 0.0125),
        "high_net_worth": (0.0045, 0.0095),
        "institutional": (0.0025, 0.0065),
    }
    low, high = ranges.get(segment, (0.0050, 0.0125))
    return float(rng.uniform(low, high))


def _net_new_assets(rng: np.random.Generator, beginning_aum: float, segment: str) -> float:
    volatility = {
        "emerging_affluent": 0.025,
        "affluent": 0.020,
        "high_net_worth": 0.016,
        "institutional": 0.012,
    }.get(segment, 0.018)
    return float(rng.normal(beginning_aum * 0.002, beginning_aum * volatility))


def _month_end_dates(months: int) -> list[str]:
    month_ends = pd.date_range(end="2026-08-31", periods=months, freq="ME")
    return [date.date().isoformat() for date in month_ends]


if __name__ == "__main__":
    generated = generate_all_synthetic_data(output_dir=DEFAULT_OUTPUT_DIR)
    for dataset_name, dataset in generated.items():
        print(f"{dataset_name}: {len(dataset):,} rows")
