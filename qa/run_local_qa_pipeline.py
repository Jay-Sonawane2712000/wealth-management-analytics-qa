"""Run the local QA pipeline end to end without Snowflake.

This script is intentionally small and local: generate clean synthetic data,
inject seeded errors, run both detector families, evaluate detections against
ground truth, and save CSV outputs under data/qa/.
"""

from __future__ import annotations

from ingestion.generate_synthetic import generate_all_synthetic_data
from qa.evaluate import combine_detection_results, evaluate_detection_results, save_evaluation_outputs
from qa.hard_rules import run_hard_rule_detection, save_detection_results
from qa.inject_errors import inject_seeded_errors, save_injected_error_outputs
from qa.statistical_rules import run_statistical_detection, save_statistical_detection_results


def run_local_qa_pipeline(seed: int = 42) -> tuple[object, object]:
    """Run the local QA pipeline and return metrics plus matched records."""
    datasets = generate_all_synthetic_data(seed=seed, months=12, validate=True)
    corrupted_performance, ground_truth = inject_seeded_errors(datasets, seed=seed)
    save_injected_error_outputs(corrupted_performance, ground_truth)

    hard_rule_results = run_hard_rule_detection(
        corrupted_performance,
        datasets["synthetic_accounts"],
        datasets["synthetic_advisors"],
        datasets["synthetic_branches"],
    )
    statistical_results = run_statistical_detection(corrupted_performance)
    save_detection_results(hard_rule_results)
    save_statistical_detection_results(statistical_results)

    combined = combine_detection_results(hard_rule_results, statistical_results)
    metrics, matches = evaluate_detection_results(ground_truth, combined)
    save_evaluation_outputs(metrics, matches)
    return metrics, matches


if __name__ == "__main__":
    metrics_df, _ = run_local_qa_pipeline()
    print(metrics_df[["evaluation_scope", "detection_family", "rule_name", "precision", "recall", "f1_score"]])
