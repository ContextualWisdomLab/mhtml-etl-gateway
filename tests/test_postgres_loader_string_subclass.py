from __future__ import annotations

from mhtml_etl_gateway.ingest_catalog import make_catalog_entry
from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import PG_BIGINT, ColumnSpec, TableSchema


class UserText(str):
    """String subtype emitted by an upstream adapter while retaining text semantics."""


class RecordingConnection:
    """Minimal transaction recorder for the live-sink adaptation boundary."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_live_sink_coerces_string_subclasses_using_schema_type() -> None:
    """String-compatible adapter values retain the same coercion contract as str."""
    schema = TableSchema(
        table_name="typed_rows",
        columns=[ColumnSpec("ID", "id_field", PG_BIGINT)],
    )
    entry = make_catalog_entry(
        sha256="a" * 64,
        table_name="typed_rows",
        path="artifact:aaaaaaaaaaaaaaaa",
        size=1,
        row_count=1,
    )
    connection = RecordingConnection()
    copied: list[tuple[object, ...]] = []
    sink = object.__new__(PsycopgSink)
    sink._conn = connection
    sink._columns_to_promote = lambda schema, rows: []
    sink._execute = lambda query, params=None: None
    sink._copy_rows = lambda query, rows: copied.extend(rows)

    inserted = sink.write_artifact_rows(
        schema,
        [[UserText("0007")]],
        source_artifact_path=entry.source_artifact_path,
        source_artifact_sha256=entry.source_artifact_sha256,
        catalog_entry=entry,
        replace_existing=False,
    )

    assert inserted == 1
    assert copied == [(7, entry.source_artifact_path, entry.source_artifact_sha256, 1)]
    assert connection.commits == 1
    assert connection.rollbacks == 0
