"""Future error injection module.

Later phases will seed known reporting issues and store labeled ground truth so
QA detection performance can be measured instead of guessed.
"""

GROUND_TRUTH_TABLE = "QA.SEEDED_ERROR_LABELS"


def planned_ground_truth_table() -> str:
    """Return the planned table for seeded QA labels."""
    return GROUND_TRUTH_TABLE
