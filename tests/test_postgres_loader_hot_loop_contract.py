"""Focused regression contracts for PostgreSQL row adaptation."""

from __future__ import annotations

from typing import Any

from mhtml_etl_gateway.ingest_catalog import make_catalog_entry
from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import ColumnSpec, PG_BIGINT, TableSchema


class _StringSubclass(str):
    """Represents a caller-provided string subtype accepted by the Sequence[str] contract."""


class _Connection:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_live_row_adapter_preserves_string_subclass_coercion(monkeypatch) -> None:
    """Hot-loop specialization must not narrow the existing ``isinstance(str)`` contract."""
    sink = object.__new__(PsycopgSink)
    connection = _Connection()
    sink._conn = connection

    copied: list[tuple[Any, ...]] = []
    monkeypatch.setattr(sink, "_columns_to_promote", lambda schema, rows: [])
    monkeypatch.setattr(sink, "_execute", lambda *args, **kwargs: None)
    monkeypatch.setattr(sink, "_copy_rows", lambda _query, rows: copied.extend(rows))

    schema = TableSchema(
        table_name="typed_rows",
        columns=[ColumnSpec("ID", "id_field", PG_BIGINT)],
    )
    catalog_entry = make_catalog_entry(
        sha256="a" * 64,
        table_name="typed_rows",
        path="artifact:aaaaaaaaaaaaaaaa",
        size=1,
        row_count=1,
    )

    inserted = sink.write_artifact_rows(
        schema,
        [[_StringSubclass("0007")]],
        source_artifact_path="artifact:aaaaaaaaaaaaaaaa",
        source_artifact_sha256="a" * 64,
        catalog_entry=catalog_entry,
        replace_existing=False,
    )

    assert inserted == 1
    assert copied == [(7, "artifact:aaaaaaaaaaaaaaaa", "a" * 64, 1)]
    assert connection.commits == 1
    assert connection.rollbacks == 0
