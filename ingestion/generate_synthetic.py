"""Future synthetic wealth-management data generation module.

Later phases will generate private-style advisor, account, household, and
monthly performance records under RAW.SYNTHETIC_* tables.
"""

SYNTHETIC_TABLE_PREFIX = "RAW.SYNTHETIC_"


def planned_table_prefix() -> str:
    """Return the planned prefix for synthetic raw Snowflake tables."""
    return SYNTHETIC_TABLE_PREFIX
