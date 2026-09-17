"""Future QA evaluation metrics module.

Later phases will compare detected anomalies to seeded ground truth and report
precision, recall, false-positive rate, and reviewer workload tradeoffs.
"""

EVALUATION_METRICS = ("precision", "recall", "false_positive_rate")


def planned_metrics() -> tuple[str, ...]:
    """Return planned QA performance metrics."""
    return EVALUATION_METRICS
