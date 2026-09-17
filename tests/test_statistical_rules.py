from qa.statistical_rules import planned_methods


def test_statistical_methods_are_declared():
    assert planned_methods() == ("z_score", "iqr")
