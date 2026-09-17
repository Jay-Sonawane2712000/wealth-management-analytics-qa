"""Future statistical anomaly checks for financial reporting QA.

Later phases will compare z-score and IQR thresholding approaches for monthly
performance and AUM movement review.
"""

STATISTICAL_METHODS = ("z_score", "iqr")


def planned_methods() -> tuple[str, ...]:
    """Return planned statistical anomaly detection methods."""
    return STATISTICAL_METHODS
