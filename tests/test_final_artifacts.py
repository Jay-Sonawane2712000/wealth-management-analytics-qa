from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
README = PROJECT_ROOT / "README.md"

KEY_ARTIFACTS = [
    "reports/generated_qa_summary.md",
    "reports/qa_evaluation_report.md",
    "outputs/excel/monthly_finance_report.xlsx",
    "outputs/powerbi/advisor_kpis.csv",
    "outputs/powerbi/branch_kpis.csv",
    "outputs/powerbi/firm_kpis.csv",
    "outputs/powerbi/qa_metrics.csv",
    "outputs/powerbi/qa_threshold_comparison.csv",
    "outputs/powerbi/wealth_management_analytics_qa.pbix",
    "docs/final_project_audit.md",
]

POWERBI_DOCS = [
    "reporting/powerbi/README.md",
    "reporting/powerbi/data_dictionary.md",
    "reporting/powerbi/dax_measures.md",
    "reporting/powerbi/dashboard_layout.md",
]


def test_key_committed_artifacts_exist():
    for relative_path in KEY_ARTIFACTS:
        assert (PROJECT_ROOT / relative_path).exists(), f"Missing artifact: {relative_path}"


def test_readme_links_completed_pbix():
    readme = README.read_text(encoding="utf-8").lower()

    assert "completed power bi report" in readme
    assert "outputs/powerbi/wealth_management_analytics_qa.pbix" in readme


def test_readme_mentions_synthetic_data():
    readme = README.read_text(encoding="utf-8").lower()

    assert "synthetic" in readme


def test_readme_mentions_precision_and_recall():
    readme = README.read_text(encoding="utf-8").lower()

    assert "precision" in readme
    assert "recall" in readme


def test_powerbi_docs_exist():
    for relative_path in POWERBI_DOCS:
        assert (PROJECT_ROOT / relative_path).exists(), f"Missing Power BI doc: {relative_path}"


def test_excel_workbook_exists():
    workbook = PROJECT_ROOT / "outputs" / "excel" / "monthly_finance_report.xlsx"

    assert workbook.exists()
    assert workbook.stat().st_size > 0
