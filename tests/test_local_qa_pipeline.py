from pathlib import Path
from uuid import uuid4

import pandas as pd

from qa.reporting import (
    format_threshold_table,
    select_operating_threshold,
    write_generated_qa_summary,
)
from qa.run_local_qa_pipeline import run_local_qa_pipeline


def _metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "evaluation_scope": "overall",
                "detection_family": "all",
                "rule_name": "all",
                "threshold_label": "z=2.5_iqr=2.0",
                "true_positives": 8,
                "false_positives": 2,
                "false_negatives": 1,
                "ground_truth_count": 9,
                "detection_count": 10,
                "precision": 0.8,
                "recall": 0.8889,
                "false_positive_rate": 0.2,
                "f1_score": 0.8421,
                "evaluated_at": "2026-01-22T00:00:00",
            }
        ]
    )


def _threshold_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "evaluation_scope": "overall",
                "threshold_label": "z=2.0_iqr=1.5",
                "precision": 0.7,
                "recall": 0.9,
                "false_positive_rate": 0.3,
                "f1_score": 0.7875,
                "true_positives": 9,
                "false_positives": 4,
                "false_negatives": 1,
            },
            {
                "evaluation_scope": "overall",
                "threshold_label": "z=2.5_iqr=2.0",
                "precision": 0.8,
                "recall": 0.8889,
                "false_positive_rate": 0.2,
                "f1_score": 0.8421,
                "true_positives": 8,
                "false_positives": 2,
                "false_negatives": 1,
            },
        ]
    )


def test_write_generated_qa_summary_creates_markdown_file():
    output_path = Path("reports") / f"test_generated_summary_{uuid4().hex}.md"
    ground_truth = pd.DataFrame({"error_type": ["negative_revenue", "extreme_revenue_spike"]})

    try:
        written_path = write_generated_qa_summary(
            _metrics(),
            _threshold_metrics(),
            ground_truth,
            pd.DataFrame(index=range(3)),
            pd.DataFrame(index=range(2)),
            output_path=output_path,
        )
        text = written_path.read_text(encoding="utf-8")

        assert "Ground Truth Injected Error Count" in text
        assert "Detection Count Summary" in text
        assert "Overall Metrics" in text
        assert "Threshold Comparison" in text
        assert "Selected Operating Threshold" in text
    finally:
        if output_path.exists():
            output_path.unlink()


def test_run_local_qa_pipeline_module_is_importable():
    assert callable(run_local_qa_pipeline)


def test_select_operating_threshold_uses_best_f1_score():
    assert select_operating_threshold(_threshold_metrics()) == "z=2.5_iqr=2.0"


def test_format_threshold_table_includes_threshold_labels():
    table = format_threshold_table(_threshold_metrics())

    assert "z=2.0_iqr=1.5" in table
    assert "z=2.5_iqr=2.0" in table
    assert "| Threshold | Precision | Recall |" in table
