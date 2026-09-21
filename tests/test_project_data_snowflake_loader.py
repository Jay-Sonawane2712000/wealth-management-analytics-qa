from datetime import date

import pandas as pd
import pytest

import ingestion.load_project_data_to_snowflake as loader
from ingestion.load_project_data_to_snowflake import (
    BOOLEAN,
    DATE,
    INTEGER,
    NUMBER,
    STRING,
    TIMESTAMP,
    DATASET_SPECS,
    DatasetSpec,
    NonEmptyTargetError,
    PreparedDataset,
    ProjectDataValidationError,
    bulk_load_prepared_data,
    ensure_all_targets_empty,
    prepare_dataframe,
    validate_csv_columns,
)


def _unit_spec() -> DatasetSpec:
    return DatasetSpec(
        source_paths=("unit.csv",),
        schema="RAW",
        table="UNIT_TABLE",
        columns=(
            ("record_id", STRING),
            ("event_date", DATE),
            ("event_timestamp", TIMESTAMP),
            ("amount", NUMBER),
            ("quantity", INTEGER),
            ("is_active", BOOLEAN),
            ("source_type", STRING),
        ),
        allowed_source_types=frozenset({"synthetic"}),
    )


def test_dataset_specs_cover_requested_destinations():
    mappings = {
        spec.qualified_name: spec.source_paths
        for spec in DATASET_SPECS
    }

    assert set(mappings) == {
        "RAW.SYNTHETIC_BRANCHES",
        "RAW.SYNTHETIC_ADVISORS",
        "RAW.SYNTHETIC_ACCOUNTS",
        "RAW.SYNTHETIC_MONTHLY_PERFORMANCE",
        "RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED",
        "QA.GROUND_TRUTH_INJECTED_ERRORS",
        "QA.DETECTION_RESULTS",
        "QA.EVALUATION_METRICS",
        "QA.DETECTION_GROUND_TRUTH_MATCHES",
    }
    assert mappings["QA.DETECTION_RESULTS"] == (
        "data/qa/detections/hard_rule_detection_results.csv",
        "data/qa/detections/statistical_detection_results.csv",
    )


def test_prepare_dataframe_converts_supported_types_and_blanks():
    raw = pd.DataFrame(
        {
            "record_id": ["001", ""],
            "event_date": ["2026-09-20", ""],
            "event_timestamp": ["2026-09-20T12:30:00+00:00", ""],
            "amount": ["123.45", ""],
            "quantity": ["7", ""],
            "is_active": ["True", "0"],
            "source_type": ["synthetic", "synthetic"],
        }
    )

    prepared = prepare_dataframe(raw, _unit_spec(), "unit.csv")

    assert prepared.columns.tolist() == [
        "RECORD_ID",
        "EVENT_DATE",
        "EVENT_TIMESTAMP",
        "AMOUNT",
        "QUANTITY",
        "IS_ACTIVE",
        "SOURCE_TYPE",
    ]
    assert prepared.loc[0, "RECORD_ID"] == "001"
    assert prepared.loc[1, "RECORD_ID"] is None
    assert prepared.loc[0, "EVENT_DATE"] == date(2026, 9, 20)
    assert prepared.loc[1, "EVENT_DATE"] is None
    assert str(prepared["EVENT_TIMESTAMP"].dtype) == "datetime64[ns]"
    assert prepared.loc[0, "AMOUNT"] == 123.45
    assert prepared.loc[0, "QUANTITY"] == 7
    assert prepared["IS_ACTIVE"].tolist() == [True, False]


def test_validate_csv_columns_rejects_missing_and_extra_columns():
    frame = pd.DataFrame(columns=["record_id", "unexpected"])

    with pytest.raises(ProjectDataValidationError, match="missing columns"):
        validate_csv_columns(frame, _unit_spec(), "unit.csv")


def test_prepare_dataframe_rejects_non_synthetic_source_type():
    raw = pd.DataFrame(
        {
            "record_id": ["1"],
            "event_date": ["2026-09-20"],
            "event_timestamp": ["2026-09-20T12:30:00Z"],
            "amount": ["1.0"],
            "quantity": ["1"],
            "is_active": ["true"],
            "source_type": ["real"],
        }
    )

    with pytest.raises(ProjectDataValidationError, match="invalid SOURCE_TYPE"):
        prepare_dataframe(raw, _unit_spec(), "unit.csv")


class FakeCursor:
    def __init__(self, counts):
        self.counts = counts
        self.current_table = None
        self.queries = []
        self.closed = False

    def execute(self, query):
        self.queries.append(query)
        self.current_table = query.split("FROM", maxsplit=1)[1].strip()

    def fetchone(self):
        return (self.counts[self.current_table],)

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, counts):
        self.cursor_instance = FakeCursor(counts)
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def test_nonempty_guard_checks_every_target_before_refusing_load():
    counts = {spec.qualified_name: 0 for spec in DATASET_SPECS}
    counts["QA.DETECTION_RESULTS"] = 5
    connection = FakeConnection(counts)

    with pytest.raises(NonEmptyTargetError, match="QA.DETECTION_RESULTS=5"):
        ensure_all_targets_empty(connection)

    assert len(connection.cursor_instance.queries) == len(DATASET_SPECS)
    assert connection.cursor_instance.closed is True


def test_bulk_loader_uses_write_pandas_arguments_and_row_count():
    spec = DatasetSpec(
        source_paths=("unit.csv",),
        schema="QA",
        table="UNIT_TABLE",
        columns=(("record_id", STRING),),
    )
    dataset = PreparedDataset(
        spec=spec,
        dataframe=pd.DataFrame({"RECORD_ID": ["1", "2"]}),
        source_row_counts={"unit.csv": 2},
    )
    calls = []

    def fake_writer(**kwargs):
        calls.append(kwargs)
        return True, 1, len(kwargs["df"]), []

    loaded = bulk_load_prepared_data(
        connection=object(),
        database="WEALTH_ANALYTICS",
        prepared={spec.qualified_name: dataset},
        writer=fake_writer,
    )

    assert loaded == {"QA.UNIT_TABLE": 2}
    assert calls[0]["table_name"] == "UNIT_TABLE"
    assert calls[0]["database"] == "WEALTH_ANALYTICS"
    assert calls[0]["schema"] == "QA"
    assert calls[0]["quote_identifiers"] is False
    assert calls[0]["auto_create_table"] is False
    assert calls[0]["overwrite"] is False


def test_run_live_load_validates_before_requesting_connection(monkeypatch):
    connection_requested = False

    def fail_validation(_project_root):
        raise ProjectDataValidationError("invalid local data")

    def unexpected_connection(_config):
        nonlocal connection_requested
        connection_requested = True

    monkeypatch.setattr(loader, "validate_and_prepare_project_data", fail_validation)
    monkeypatch.setattr(loader, "get_connection", unexpected_connection)

    with pytest.raises(ProjectDataValidationError, match="invalid local data"):
        loader.run_live_load()

    assert connection_requested is False


def test_run_live_load_closes_connection_when_guard_fails(monkeypatch):
    connection = FakeConnection({})
    monkeypatch.setattr(loader, "validate_and_prepare_project_data", lambda _root: {})
    monkeypatch.setattr(loader, "get_snowflake_config", lambda: {"database": "DB"})
    monkeypatch.setattr(loader, "get_connection", lambda _config: connection)
    monkeypatch.setattr(
        loader,
        "ensure_all_targets_empty",
        lambda _connection: (_ for _ in ()).throw(NonEmptyTargetError("not empty")),
    )

    with pytest.raises(NonEmptyTargetError, match="not empty"):
        loader.run_live_load()

    assert connection.closed is True
