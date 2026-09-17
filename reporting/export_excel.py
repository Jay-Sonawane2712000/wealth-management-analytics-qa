"""Future Excel export module.

Later phases will export monthly finance summaries, KPI tables, and QA
evaluation outputs to Excel workbooks for stakeholder review.
"""

DEFAULT_REPORT_NAME = "monthly_finance_summary.xlsx"


def default_report_name() -> str:
    """Return the planned default Excel report file name."""
    return DEFAULT_REPORT_NAME
