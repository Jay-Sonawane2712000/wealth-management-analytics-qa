from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pandas as pd
import pytest

from reporting.export_powerbi_csvs import EXPECTED_EXPORTS, export_powerbi_csvs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POWERBI_DOCS = PROJECT_ROOT / "reporting" / "powerbi"


@pytest.fixture(scope="module")
def local_export_dir():
    path = PROJECT_ROOT / "outputs" / "powerbi" / f"test_exports_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        if path.exists():
            rmtree(path)


@pytest.fixture(scope="module")
def exported_powerbi_csvs(local_export_dir):
    export_powerbi_csvs(output_dir=local_export_dir, seed=202)
    return local_export_dir


def test_export_powerbi_csvs_writes_expected_files(exported_powerbi_csvs):
    outputs = {name: exported_powerbi_csvs / file_name for name, file_name in EXPECTED_EXPORTS.items()}

    assert set(outputs) == set(EXPECTED_EXPORTS)
    for file_name in EXPECTED_EXPORTS.values():
        path = exported_powerbi_csvs / file_name
        assert path.exists()
        assert len(pd.read_csv(path)) > 0


def test_qa_metrics_contains_precision_and_recall(exported_powerbi_csvs):
    qa_metrics = pd.read_csv(exported_powerbi_csvs / "qa_metrics.csv")
    assert "precision" in qa_metrics.columns
    assert "recall" in qa_metrics.columns


def test_qa_threshold_comparison_contains_threshold_label(exported_powerbi_csvs):
    threshold_comparison = pd.read_csv(exported_powerbi_csvs / "qa_threshold_comparison.csv")
    assert "threshold_label" in threshold_comparison.columns


def test_powerbi_readme_states_no_pbix_is_included():
    readme = (POWERBI_DOCS / "README.md").read_text(encoding="utf-8").lower()

    assert "finished `.pbix` file is not included" in readme
    assert "power bi-ready reporting layer" in readme


def test_dax_measures_include_core_finance_and_qa_measures():
    dax = (POWERBI_DOCS / "dax_measures.md").read_text(encoding="utf-8")

    assert "Total Revenue =" in dax
    assert "Precision =" in dax
    assert "Recall =" in dax


def test_dashboard_layout_includes_qa_review_page():
    layout = (POWERBI_DOCS / "dashboard_layout.md").read_text(encoding="utf-8")

    assert "Page 3: QA & Anomaly Review" in layout
