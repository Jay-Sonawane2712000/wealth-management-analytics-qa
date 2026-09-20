from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R_SCRIPT = PROJECT_ROOT / "r" / "advisor_aum_growth_model.R"
R_README = PROJECT_ROOT / "r" / "README.md"
README = PROJECT_ROOT / "README.md"
R_REPORT = PROJECT_ROOT / "reports" / "r_aum_growth_model_summary.md"


def test_r_aum_growth_model_script_exists():
    assert R_SCRIPT.exists()


def test_r_script_contains_expected_model_terms():
    script = R_SCRIPT.read_text(encoding="utf-8")

    assert "advisor_tenure_years" in script
    assert "fee_rate" in script
    assert "client_segment" in script
    assert "primary_client_segment" in script
    assert "aum_growth_rate ~ advisor_tenure_years + fee_rate + client_segment + primary_client_segment" in script


def test_r_script_references_expected_markdown_report():
    script = R_SCRIPT.read_text(encoding="utf-8")

    assert "reports" in script
    assert "r_aum_growth_model_summary.md" in script


def test_r_readme_exists_and_includes_run_command():
    assert R_README.exists()

    readme = R_README.read_text(encoding="utf-8")
    assert "Rscript r/advisor_aum_growth_model.R" in readme
    assert "readr" in readme
    assert "dplyr" in readme
    assert "ggplot2" in readme
    assert "broom" in readme


def test_project_readme_includes_rscript_command():
    readme = README.read_text(encoding="utf-8")

    assert 'C:\\Program Files\\R\\R-4.6.1\\bin\\Rscript.exe" r/advisor_aum_growth_model.R' in readme


def test_generated_r_report_exists_and_contains_required_sections():
    assert R_REPORT.exists()

    report = R_REPORT.read_text(encoding="utf-8")
    for section in ("Purpose", "Model Formula", "Coefficient Summary", "Limitations"):
        assert section in report
