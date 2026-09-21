"""Deploy and verify the project's Snowflake views safely.

This module uses Snowflake's structured SQL splitter, reuses the existing
credential-safe connection helpers, sanitizes connector failures, and always
closes cursors and connections. It can be run with:

    python -m ingestion.deploy_snowflake_views
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Callable, Sequence

from snowflake.connector.util_text import split_statements

from ingestion.load_sec_adv_to_snowflake import get_connection, get_snowflake_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_FILES = ("sql/kpi_views.sql", "sql/qa_views.sql")

EXPECTED_VIEWS = frozenset(
    {
        ("ANALYTICS", "ADVISOR_MONTHLY_KPIS"),
        ("ANALYTICS", "BRANCH_MONTHLY_KPIS"),
        ("ANALYTICS", "FIRM_MONTHLY_KPIS"),
        ("REPORTING", "EXECUTIVE_MONTHLY_SUMMARY"),
        ("QA", "BASELINE_DATA_HEALTH_SUMMARY"),
        ("QA", "HARD_RULE_DETECTION_RESULTS"),
        ("QA", "STATISTICAL_DETECTION_RESULTS"),
    }
)

VIEW_COUNT_QUERIES = (
    ("ANALYTICS.ADVISOR_MONTHLY_KPIS", "SELECT COUNT(*) FROM ANALYTICS.ADVISOR_MONTHLY_KPIS"),
    ("ANALYTICS.BRANCH_MONTHLY_KPIS", "SELECT COUNT(*) FROM ANALYTICS.BRANCH_MONTHLY_KPIS"),
    ("ANALYTICS.FIRM_MONTHLY_KPIS", "SELECT COUNT(*) FROM ANALYTICS.FIRM_MONTHLY_KPIS"),
    (
        "REPORTING.EXECUTIVE_MONTHLY_SUMMARY",
        "SELECT COUNT(*) FROM REPORTING.EXECUTIVE_MONTHLY_SUMMARY",
    ),
    (
        "QA.HARD_RULE_DETECTION_RESULTS",
        "SELECT COUNT(*) FROM QA.HARD_RULE_DETECTION_RESULTS",
    ),
    (
        "QA.STATISTICAL_DETECTION_RESULTS",
        "SELECT COUNT(*) FROM QA.STATISTICAL_DETECTION_RESULTS",
    ),
)

VIEW_METADATA_QUERY = """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM WEALTH_ANALYTICS.INFORMATION_SCHEMA.VIEWS
WHERE
    (TABLE_SCHEMA = 'ANALYTICS' AND TABLE_NAME IN (
        'ADVISOR_MONTHLY_KPIS',
        'BRANCH_MONTHLY_KPIS',
        'FIRM_MONTHLY_KPIS'
    ))
    OR (TABLE_SCHEMA = 'REPORTING' AND TABLE_NAME = 'EXECUTIVE_MONTHLY_SUMMARY')
    OR (TABLE_SCHEMA = 'QA' AND TABLE_NAME IN (
        'BASELINE_DATA_HEALTH_SUMMARY',
        'HARD_RULE_DETECTION_RESULTS',
        'STATISTICAL_DETECTION_RESULTS'
    ))
ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

BASELINE_HEALTH_QUERY = """
SELECT CHECK_NAME, ISSUE_COUNT, STATUS
FROM QA.BASELINE_DATA_HEALTH_SUMMARY
ORDER BY CHECK_NAME
"""


class ViewDeploymentError(RuntimeError):
    """Base error for safe deployment and verification failures."""


class StatementExecutionError(ViewDeploymentError):
    """Sanitized context for one failed SQL-file statement."""

    def __init__(self, statement: "SqlStatement", cause: Exception):
        self.source_file = statement.source_file
        self.sequence = statement.sequence
        self.exception_type = type(cause).__name__
        self.error_code = getattr(cause, "errno", None)
        self.sqlstate = getattr(cause, "sqlstate", None)
        super().__init__(
            f"{self.source_file} statement {self.sequence} failed; "
            f"{self.exception_type}; error code={self.error_code}; SQLSTATE={self.sqlstate}"
        )


@dataclass(frozen=True)
class SqlStatement:
    source_file: str
    sequence: int
    sql: str


@dataclass(frozen=True)
class DeploymentResult:
    executed_statements: tuple[SqlStatement, ...]
    verified_views: tuple[str, ...]
    row_counts: dict[str, int]
    baseline_health: tuple[tuple[str, int, str], ...]
    warehouse_status: str


def load_sql_statements(
    project_root: str | Path = PROJECT_ROOT,
    sql_files: Sequence[str] = SQL_FILES,
) -> list[SqlStatement]:
    """Read SQL files in order and split them with Snowflake's parser."""
    root = Path(project_root)
    statements: list[SqlStatement] = []
    for relative_path in sql_files:
        path = root / relative_path
        if not path.is_file():
            raise ViewDeploymentError(f"SQL file not found: {relative_path}")

        sql_text = path.read_text(encoding="utf-8")
        sequence = 0
        for statement, _ in split_statements(StringIO(sql_text), remove_comments=True):
            if not statement.strip():
                continue
            sequence += 1
            statements.append(SqlStatement(relative_path, sequence, statement))

    return statements


def configure_session(cursor) -> None:
    """Explicitly select the required role, warehouse, and database."""
    cursor.execute("USE ROLE WEALTH_ANALYTICS_ROLE")
    cursor.execute("USE WAREHOUSE ANALYTICS_WH")
    cursor.execute("USE DATABASE WEALTH_ANALYTICS")


def execute_statements(
    cursor,
    statements: Sequence[SqlStatement],
    reporter: Callable[[str], None] | None = None,
) -> tuple[SqlStatement, ...]:
    """Execute SQL statements in order and report file/sequence after success."""
    executed: list[SqlStatement] = []
    for statement in statements:
        try:
            cursor.execute(statement.sql)
        except Exception as exc:
            raise StatementExecutionError(statement, exc) from None
        executed.append(statement)
        if reporter is not None:
            reporter(f"Executed {statement.source_file} statement {statement.sequence}")
    return tuple(executed)


def verify_expected_views(cursor) -> tuple[str, ...]:
    """Require all seven expected views in Snowflake metadata."""
    cursor.execute(VIEW_METADATA_QUERY)
    found = {(str(row[0]), str(row[1])) for row in cursor.fetchall()}
    missing = EXPECTED_VIEWS - found
    if missing:
        names = ", ".join(f"{schema}.{view}" for schema, view in sorted(missing))
        raise ViewDeploymentError(f"Expected views missing after deployment: {names}")
    return tuple(f"{schema}.{view}" for schema, view in sorted(EXPECTED_VIEWS))


def query_view_row_counts(cursor) -> dict[str, int]:
    """Return row counts for the six requested reporting and QA views."""
    counts: dict[str, int] = {}
    for name, query in VIEW_COUNT_QUERIES:
        cursor.execute(query)
        counts[name] = int(cursor.fetchone()[0])
    return counts


def query_baseline_health(cursor) -> tuple[tuple[str, int, str], ...]:
    """Return every baseline health row in CHECK_NAME order."""
    cursor.execute(BASELINE_HEALTH_QUERY)
    return tuple((str(row[0]), int(row[1]), str(row[2])) for row in cursor.fetchall())


def is_already_suspended_error(exc: Exception) -> bool:
    """Recognize Snowflake's harmless already-suspended warehouse response."""
    return getattr(exc, "errno", None) == 90064 or "already suspended" in str(exc).lower()


def suspend_warehouse(connection) -> str:
    """Suspend the analytics warehouse, treating an existing suspension as success."""
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("ALTER WAREHOUSE ANALYTICS_WH SUSPEND")
        return "suspended"
    except Exception as exc:
        if is_already_suspended_error(exc):
            return "already suspended"
        raise
    finally:
        if cursor is not None:
            cursor.close()


def deploy_and_verify(
    project_root: str | Path = PROJECT_ROOT,
    reporter: Callable[[str], None] | None = None,
) -> DeploymentResult:
    """Deploy views, verify outputs, suspend the warehouse, and close resources."""
    statements = load_sql_statements(project_root)
    connection = None
    cursor = None
    primary_error: Exception | None = None
    suspension_error: Exception | None = None
    executed: tuple[SqlStatement, ...] = ()
    verified_views: tuple[str, ...] = ()
    row_counts: dict[str, int] = {}
    baseline_health: tuple[tuple[str, int, str], ...] = ()
    warehouse_status = "not attempted"

    try:
        connection = get_connection(get_snowflake_config())
        cursor = connection.cursor()
        configure_session(cursor)
        executed = execute_statements(cursor, statements, reporter=reporter)
        verified_views = verify_expected_views(cursor)
        row_counts = query_view_row_counts(cursor)
        baseline_health = query_baseline_health(cursor)
    except Exception as exc:
        primary_error = exc
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if connection is not None:
            try:
                warehouse_status = suspend_warehouse(connection)
            except Exception as exc:
                suspension_error = exc
            finally:
                try:
                    connection.close()
                except Exception:
                    pass

    if primary_error is not None:
        raise primary_error
    if suspension_error is not None:
        raise suspension_error

    return DeploymentResult(
        executed_statements=executed,
        verified_views=verified_views,
        row_counts=row_counts,
        baseline_health=baseline_health,
        warehouse_status=warehouse_status,
    )


def _print_sanitized_error(exc: Exception) -> None:
    if isinstance(exc, StatementExecutionError):
        print(f"Failing statement: {exc.source_file} statement {exc.sequence}", file=sys.stderr)
        exception_type = exc.exception_type
        error_code = exc.error_code
        sqlstate = exc.sqlstate
    else:
        exception_type = type(exc).__name__
        error_code = getattr(exc, "errno", None)
        sqlstate = getattr(exc, "sqlstate", None)

    print(f"Exception type: {exception_type}", file=sys.stderr)
    print(f"Error code: {error_code}", file=sys.stderr)
    print(f"SQLSTATE: {sqlstate}", file=sys.stderr)
    print(
        "Sanitized message: Snowflake view deployment or verification did not complete.",
        file=sys.stderr,
    )


def main() -> int:
    try:
        result = deploy_and_verify(reporter=print)
    except Exception as exc:
        _print_sanitized_error(exc)
        return 1

    print(f"Expected views present: {len(result.verified_views)} of {len(EXPECTED_VIEWS)}")
    for view in result.verified_views:
        print(f"View present: {view}")
    for view, count in result.row_counts.items():
        print(f"{view}: {count}")
    print("QA.BASELINE_DATA_HEALTH_SUMMARY:")
    for check_name, issue_count, status in result.baseline_health:
        print(f"  {check_name}: issue_count={issue_count}, status={status}")
    print(f"Warehouse status: {result.warehouse_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
