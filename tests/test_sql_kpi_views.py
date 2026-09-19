from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_sql(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8").upper()


def test_kpi_views_sql_exists():
    assert (PROJECT_ROOT / "sql" / "kpi_views.sql").exists()


def test_kpi_views_defines_required_views():
    sql = _read_sql("sql/kpi_views.sql")

    required_views = [
        "ANALYTICS.ADVISOR_MONTHLY_KPIS",
        "ANALYTICS.BRANCH_MONTHLY_KPIS",
        "ANALYTICS.FIRM_MONTHLY_KPIS",
        "REPORTING.EXECUTIVE_MONTHLY_SUMMARY",
    ]
    for view_name in required_views:
        assert f"CREATE OR REPLACE VIEW {view_name}" in sql


def test_kpi_views_reference_real_and_synthetic_raw_tables():
    sql = _read_sql("sql/kpi_views.sql")

    required_tables = [
        "RAW.SEC_ADV_FIRMS",
        "RAW.SYNTHETIC_BRANCHES",
        "RAW.SYNTHETIC_ADVISORS",
        "RAW.SYNTHETIC_ACCOUNTS",
        "RAW.SYNTHETIC_MONTHLY_PERFORMANCE",
    ]
    for table_name in required_tables:
        assert table_name in sql


def test_kpi_views_use_safe_division_and_qa_placeholder():
    sql = _read_sql("sql/kpi_views.sql")

    assert "NULLIF" in sql
    assert "QA_NOT_RUN_YET" in sql


def test_qa_views_define_baseline_health_summary_without_final_anomaly_claim():
    sql = _read_sql("sql/qa_views.sql")

    assert "CREATE OR REPLACE VIEW QA.BASELINE_DATA_HEALTH_SUMMARY" in sql
    assert "FINAL ANOMALY DETECTION" in sql
    assert "CREATE OR REPLACE VIEW QA.DETECTED_ANOMALIES" not in sql
    assert "CREATE OR REPLACE VIEW QA.ANOMALY" not in sql


def test_qa_views_define_hard_rule_detection_results():
    sql = _read_sql("sql/qa_views.sql")

    assert "CREATE OR REPLACE VIEW QA.HARD_RULE_DETECTION_RESULTS" in sql
    assert "RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED" in sql
    assert "NEGATIVE_ENDING_AUM" in sql
    assert "DUPLICATE_ACCOUNT_MONTH" in sql
    assert "REVENUE_ON_CLOSED_ACCOUNT" in sql
