"""Export Power BI-ready finance KPI and QA evaluation CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ingestion.generate_synthetic import generate_all_synthetic_data
from qa.evaluate import combine_detection_results, evaluate_detection_results, run_threshold_comparison
from qa.hard_rules import run_hard_rule_detection
from qa.inject_errors import inject_seeded_errors
from qa.statistical_rules import run_statistical_detection
from reporting.export_excel import (
    DEFAULT_IQR_MULTIPLIER,
    DEFAULT_Z_THRESHOLD,
    calculate_excel_kpi_tables,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "powerbi"
DEFAULT_MONTHS = 8
DEFAULT_MAX_FIRMS = 2
EXPECTED_EXPORTS = {
    "advisor_kpis": "advisor_kpis.csv",
    "branch_kpis": "branch_kpis.csv",
    "firm_kpis": "firm_kpis.csv",
    "qa_metrics": "qa_metrics.csv",
    "qa_threshold_comparison": "qa_threshold_comparison.csv",
}


def build_powerbi_export_data(seed: int = 42) -> dict[str, pd.DataFrame]:
    """Build small local tables that can be imported into Power BI."""
    datasets = generate_all_synthetic_data(
        seed=seed,
        months=DEFAULT_MONTHS,
        max_firms=DEFAULT_MAX_FIRMS,
        validate=True,
    )
    kpis = calculate_excel_kpi_tables(datasets)

    corrupted_performance, ground_truth = inject_seeded_errors(datasets, seed=seed)
    hard_rule_results = run_hard_rule_detection(
        corrupted_performance,
        datasets["synthetic_accounts"],
        datasets["synthetic_advisors"],
        datasets["synthetic_branches"],
    )
    statistical_results = run_statistical_detection(
        corrupted_performance,
        z_threshold=DEFAULT_Z_THRESHOLD,
        iqr_multiplier=DEFAULT_IQR_MULTIPLIER,
    )
    combined = combine_detection_results(hard_rule_results, statistical_results)
    threshold_label = f"z={DEFAULT_Z_THRESHOLD}_iqr={DEFAULT_IQR_MULTIPLIER}"
    qa_metrics, _ = evaluate_detection_results(
        ground_truth,
        combined,
        threshold_label=threshold_label,
    )
    qa_threshold_comparison = run_threshold_comparison(
        corrupted_performance,
        ground_truth,
        hard_rule_results,
        z_thresholds=(2.0, 2.5, 3.0),
        iqr_multipliers=(1.5, 2.0, 3.0),
    )

    return {
        "advisor_kpis": kpis["advisor_kpis"],
        "branch_kpis": kpis["branch_kpis"],
        "firm_kpis": kpis["firm_kpis"],
        "qa_metrics": qa_metrics,
        "qa_threshold_comparison": qa_threshold_comparison,
    }


def export_powerbi_csvs(output_dir: str | Path | None = None, seed: int = 42) -> dict[str, Path]:
    """Export Power BI-ready CSV files and return their paths."""
    path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)

    export_data = build_powerbi_export_data(seed=seed)
    output_paths: dict[str, Path] = {}
    for table_name, file_name in EXPECTED_EXPORTS.items():
        file_path = path / file_name
        export_data[table_name].to_csv(file_path, index=False)
        output_paths[table_name] = file_path

    return output_paths


if __name__ == "__main__":
    outputs = export_powerbi_csvs()
    print("Power BI CSV exports written:")
    for table_name, path in outputs.items():
        print(f"- {table_name}: {path}")
