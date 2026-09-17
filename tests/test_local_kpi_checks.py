import pandas as pd
import pytest

from qa.local_kpi_checks import (
    calculate_advisor_monthly_kpis,
    calculate_branch_monthly_kpis,
    calculate_firm_monthly_kpis,
)


def _performance_sample() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "month_end_date": "2026-08-31",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "advisor_id": "ADV-001",
                "account_id": "ACCT-001",
                "beginning_aum": 100.0,
                "ending_aum": 120.0,
                "net_new_assets": 10.0,
                "revenue": 1.2,
                "fee_rate": 0.012,
            },
            {
                "month_end_date": "2026-08-31",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "advisor_id": "ADV-001",
                "account_id": "ACCT-002",
                "beginning_aum": 300.0,
                "ending_aum": 330.0,
                "net_new_assets": 20.0,
                "revenue": 3.6,
                "fee_rate": 0.010,
            },
            {
                "month_end_date": "2026-08-31",
                "firm_crd_number": "100001",
                "branch_id": "BR-001",
                "advisor_id": "ADV-002",
                "account_id": "ACCT-003",
                "beginning_aum": 600.0,
                "ending_aum": 660.0,
                "net_new_assets": 30.0,
                "revenue": 6.0,
                "fee_rate": 0.008,
            },
        ]
    )


def test_advisor_kpis_calculate_aum_growth_and_revenue_per_account():
    result = calculate_advisor_monthly_kpis(_performance_sample())
    advisor = result[result["advisor_id"] == "ADV-001"].iloc[0]

    assert advisor["aum_growth_rate"] == pytest.approx(0.125)
    assert advisor["revenue_per_account"] == pytest.approx(2.4)


def test_branch_kpis_calculate_revenue_per_advisor():
    result = calculate_branch_monthly_kpis(_performance_sample())
    branch = result.iloc[0]

    assert branch["revenue_per_advisor"] == pytest.approx(5.4)


def test_firm_kpis_calculate_aum_growth_rate():
    result = calculate_firm_monthly_kpis(_performance_sample())
    firm = result.iloc[0]

    assert firm["aum_growth_rate"] == pytest.approx(0.11)
