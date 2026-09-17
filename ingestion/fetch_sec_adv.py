"""Future SEC/IAPD Form ADV ingestion module.

Later phases will fetch or stage public investment adviser firm data for the
RAW.SEC_ADV_FIRMS table. This scaffold intentionally avoids network access and
Snowflake writes.
"""

SEC_ADV_TARGET_TABLE = "RAW.SEC_ADV_FIRMS"


def planned_target_table() -> str:
    """Return the planned Snowflake target table for public adviser data."""
    return SEC_ADV_TARGET_TABLE
