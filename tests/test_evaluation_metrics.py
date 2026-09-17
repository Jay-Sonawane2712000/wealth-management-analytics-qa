from qa.evaluate import planned_metrics
from qa.inject_errors import planned_ground_truth_table


def test_qa_evaluation_scaffold_is_declared():
    assert planned_ground_truth_table() == "QA.GROUND_TRUTH_INJECTED_ERRORS"
    assert "precision" in planned_metrics()
    assert "recall" in planned_metrics()
    assert "false_positive_rate" in planned_metrics()
