"""Run the local QA pipeline end to end without Snowflake.

This script is intentionally small and local: generate clean synthetic data,
inject seeded errors, run both detector families, evaluate detections against
ground truth, and save CSV outputs under data/qa/.
"""

from __future__ import annotations

from ingestion.generate_synthetic import generate_all_synthetic_data
from pathlib import Path

from qa.evaluate import (
    combine_detection_results,
    evaluate_detection_results,
    run_threshold_comparison,
    save_evaluation_outputs,
)
from qa.hard_rules import run_hard_rule_detection, save_detection_results
from qa.inject_errors import inject_seeded_errors, save_injected_error_outputs
from qa.reporting import select_overall_metrics, select_operating_threshold, write_generated_qa_summary
from qa.statistical_rules import run_statistical_detection, save_statistical_detection_results

DEFAULT_Z_THRESHOLD = 2.5
DEFAULT_IQR_MULTIPLIER = 2.0
DEFAULT_PIPELINE_MONTHS = 8
DEFAULT_PIPELINE_MAX_FIRMS = 2
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_OUTPUT_DIR = PROJECT_ROOT / "data" / "qa" / "evaluation"


def run_local_qa_pipeline(
    seed: int = 42,
    months: int = DEFAULT_PIPELINE_MONTHS,
    max_firms: int = DEFAULT_PIPELINE_MAX_FIRMS,
) -> dict[str, object]:
    """Run the full local QA pipeline and return generated DataFrames/paths."""
    datasets = generate_all_synthetic_data(
        seed=seed,
        months=months,
        max_firms=max_firms,
        validate=True,
    )
    corrupted_performance, ground_truth = inject_seeded_errors(datasets, seed=seed)
    save_injected_error_outputs(corrupted_performance, ground_truth)

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
    save_detection_results(hard_rule_results)
    save_statistical_detection_results(statistical_results)

    combined = combine_detection_results(hard_rule_results, statistical_results)
    default_threshold_label = f"z={DEFAULT_Z_THRESHOLD}_iqr={DEFAULT_IQR_MULTIPLIER}"
    metrics, matches = evaluate_detection_results(
        ground_truth,
        combined,
        threshold_label=default_threshold_label,
    )
    save_evaluation_outputs(metrics, matches)

    threshold_metrics = run_threshold_comparison(
        corrupted_performance,
        ground_truth,
        hard_rule_results,
        z_thresholds=(2.0, 2.5, 3.0),
        iqr_multipliers=(1.5, 2.0, 3.0),
    )
    EVALUATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    threshold_metrics.to_csv(EVALUATION_OUTPUT_DIR / "threshold_comparison_metrics.csv", index=False)

    summary_path = write_generated_qa_summary(
        metrics,
        threshold_metrics,
        ground_truth,
        hard_rule_results,
        statistical_results,
    )
    return {
        "metrics": metrics,
        "matches": matches,
        "threshold_metrics": threshold_metrics,
        "ground_truth": ground_truth,
        "hard_rule_results": hard_rule_results,
        "statistical_results": statistical_results,
        "summary_path": summary_path,
        "selected_threshold": select_operating_threshold(threshold_metrics),
    }


if __name__ == "__main__":
    outputs = run_local_qa_pipeline()
    overall = select_overall_metrics(outputs["metrics"])
    print("Local QA pipeline complete")
    print(f"Injected errors: {len(outputs['ground_truth'])}")
    print(f"Hard-rule detections: {len(outputs['hard_rule_results'])}")
    print(f"Statistical detections: {len(outputs['statistical_results'])}")
    print(f"Overall precision: {overall.get('precision', 0):.3f}")
    print(f"Overall recall: {overall.get('recall', 0):.3f}")
    print(f"False-positive rate: {overall.get('false_positive_rate', 0):.3f}")
    print(f"Selected threshold label: {outputs['selected_threshold']}")
    print(f"Summary report: {outputs['summary_path']}")
