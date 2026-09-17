from qa.hard_rules import available_rule_categories


def test_hard_rule_categories_are_declared():
    assert "validity" in available_rule_categories()
