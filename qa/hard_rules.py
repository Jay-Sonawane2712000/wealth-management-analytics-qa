"""Future hard-rule anomaly checks for financial reporting QA.

Later phases will hold deterministic checks such as impossible returns, missing
advisor mappings, duplicate account keys, and negative AUM.
"""

HARD_RULE_CATEGORIES = ("completeness", "validity", "relationship", "duplicate")


def available_rule_categories() -> tuple[str, ...]:
    """Return planned hard-rule category names."""
    return HARD_RULE_CATEGORIES
