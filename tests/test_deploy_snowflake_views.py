import pytest

import ingestion.deploy_snowflake_views as deployer
from ingestion.deploy_snowflake_views import (
    EXPECTED_VIEWS,
    SqlStatement,
    StatementExecutionError,
    ViewDeploymentError,
    execute_statements,
    load_sql_statements,
    suspend_warehouse,
    verify_expected_views,
)


class RecordingCursor:
    def __init__(self, rows=None, execute_error=None):
        self.rows = list(rows or [])
        self.execute_error = execute_error
        self.executed = []
        self.closed = False

    def execute(self, statement):
        self.executed.append(statement)
        if self.execute_error is not None:
            raise self.execute_error
        return self

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class SequencedConnection:
    def __init__(self, cursors):
        self.cursors = iter(cursors)
        self.closed = False

    def cursor(self):
        return next(self.cursors)

    def close(self):
        self.closed = True


def test_load_sql_statements_uses_expected_file_order_and_sequences():
    statements = load_sql_statements()

    assert len(statements) == 7
    assert [(item.source_file, item.sequence) for item in statements] == [
        ("sql/kpi_views.sql", 1),
        ("sql/kpi_views.sql", 2),
        ("sql/kpi_views.sql", 3),
        ("sql/kpi_views.sql", 4),
        ("sql/qa_views.sql", 1),
        ("sql/qa_views.sql", 2),
        ("sql/qa_views.sql", 3),
    ]
    assert all(item.sql.strip() for item in statements)


def test_execute_statements_runs_in_order_and_reports_source_sequence():
    cursor = RecordingCursor()
    statements = [
        SqlStatement("first.sql", 1, "SELECT 1"),
        SqlStatement("second.sql", 1, "SELECT 2"),
    ]
    reports = []

    executed = execute_statements(cursor, statements, reporter=reports.append)

    assert executed == tuple(statements)
    assert cursor.executed == ["SELECT 1", "SELECT 2"]
    assert reports == [
        "Executed first.sql statement 1",
        "Executed second.sql statement 1",
    ]


def test_execute_statements_stops_and_sanitizes_failure_context():
    class FakeConnectorError(Exception):
        errno = 1234
        sqlstate = "42000"

    cursor = RecordingCursor(execute_error=FakeConnectorError("credential-like details"))
    statement = SqlStatement("sql/kpi_views.sql", 2, "CREATE VIEW broken")

    with pytest.raises(StatementExecutionError) as captured:
        execute_statements(cursor, [statement])

    error = captured.value
    assert error.source_file == "sql/kpi_views.sql"
    assert error.sequence == 2
    assert error.exception_type == "FakeConnectorError"
    assert error.error_code == 1234
    assert error.sqlstate == "42000"
    assert "credential-like details" not in str(error)


def test_verify_expected_views_requires_all_seven():
    rows = sorted(EXPECTED_VIEWS)
    cursor = RecordingCursor(rows=rows)

    verified = verify_expected_views(cursor)

    assert len(verified) == 7
    assert cursor.executed == [deployer.VIEW_METADATA_QUERY]


def test_verify_expected_views_reports_missing_view():
    rows = sorted(EXPECTED_VIEWS)[:-1]
    cursor = RecordingCursor(rows=rows)

    with pytest.raises(ViewDeploymentError, match="Expected views missing"):
        verify_expected_views(cursor)


def test_deploy_and_verify_closes_resources_and_suspends(monkeypatch):
    main_cursor = RecordingCursor()
    suspension_cursor = RecordingCursor()
    connection = SequencedConnection([main_cursor, suspension_cursor])
    statements = [SqlStatement("sql/kpi_views.sql", 1, "SELECT 1")]

    monkeypatch.setattr(deployer, "load_sql_statements", lambda _root: statements)
    monkeypatch.setattr(deployer, "get_snowflake_config", lambda: {"database": "DB"})
    monkeypatch.setattr(deployer, "get_connection", lambda _config: connection)
    monkeypatch.setattr(deployer, "configure_session", lambda _cursor: None)
    monkeypatch.setattr(
        deployer,
        "execute_statements",
        lambda _cursor, _statements, reporter=None: tuple(_statements),
    )
    monkeypatch.setattr(
        deployer,
        "verify_expected_views",
        lambda _cursor: tuple(f"{schema}.{view}" for schema, view in sorted(EXPECTED_VIEWS)),
    )
    monkeypatch.setattr(deployer, "query_view_row_counts", lambda _cursor: {"VIEW": 1})
    monkeypatch.setattr(deployer, "query_baseline_health", lambda _cursor: (("check", 0, "PASS"),))

    result = deployer.deploy_and_verify()

    assert result.warehouse_status == "suspended"
    assert main_cursor.closed is True
    assert suspension_cursor.closed is True
    assert suspension_cursor.executed == ["ALTER WAREHOUSE ANALYTICS_WH SUSPEND"]
    assert connection.closed is True


def test_deploy_and_verify_closes_and_suspends_after_failure(monkeypatch):
    main_cursor = RecordingCursor()
    suspension_cursor = RecordingCursor()
    connection = SequencedConnection([main_cursor, suspension_cursor])

    monkeypatch.setattr(deployer, "load_sql_statements", lambda _root: [])
    monkeypatch.setattr(deployer, "get_snowflake_config", lambda: {})
    monkeypatch.setattr(deployer, "get_connection", lambda _config: connection)
    monkeypatch.setattr(deployer, "configure_session", lambda _cursor: None)
    monkeypatch.setattr(
        deployer,
        "execute_statements",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ViewDeploymentError("failed")),
    )

    with pytest.raises(ViewDeploymentError, match="failed"):
        deployer.deploy_and_verify()

    assert main_cursor.closed is True
    assert suspension_cursor.closed is True
    assert suspension_cursor.executed == ["ALTER WAREHOUSE ANALYTICS_WH SUSPEND"]
    assert connection.closed is True


def test_already_suspended_is_successful_noop_and_cursor_closes():
    class AlreadySuspendedError(Exception):
        errno = 90064

    cursor = RecordingCursor(execute_error=AlreadySuspendedError("warehouse already suspended"))
    connection = SequencedConnection([cursor])

    status = suspend_warehouse(connection)

    assert status == "already suspended"
    assert cursor.closed is True
