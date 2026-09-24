"""Focused regression contracts for PostgreSQL row adaptation."""

from __future__ import annotations

from typing import Any

from mhtml_etl_gateway.ingest_catalog import make_catalog_entry
from mhtml_etl_gateway.postgres_loader import PsycopgSink, prepare_typed_rows
from mhtml_etl_gateway.schema_inference import (
    ColumnSpec,
    PG_BIGINT,
    PG_TEXT,
    TableSchema,
)


class _StringSubclass(str):
    """A string subtype accepted by the existing row-value contract."""


class _Connection:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def _sink_with_capture(monkeypatch) -> tuple[PsycopgSink, _Connection, list[tuple[Any, ...]]]:
    sink = object.__new__(PsycopgSink)
    connection = _Connection()
    sink._conn = connection
    copied: list[tuple[Any, ...]] = []
    monkeypatch.setattr(sink, "_columns_to_promote", lambda schema, rows: [])
    monkeypatch.setattr(sink, "_execute", lambda *args, **kwargs: None)
    monkeypatch.setattr(sink, "_copy_rows", lambda _query, rows: copied.extend(rows))
    return sink, connection, copied


def test_live_row_adapter_preserves_string_subclass_coercion(monkeypatch) -> None:
    """Hot-loop specialization must preserve the existing string-family contract."""
    sink, connection, copied = _sink_with_capture(monkeypatch)
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


def test_live_row_adapter_preserves_missing_short_row_cell(monkeypatch) -> None:
    """The short-row branch must write one NULL for each missing schema column."""
    sink, connection, copied = _sink_with_capture(monkeypatch)
    schema = TableSchema(
        table_name="short_rows",
        columns=[
            ColumnSpec("A", "a_field", PG_TEXT),
            ColumnSpec("B", "b_field", PG_TEXT),
        ],
    )
    catalog_entry = make_catalog_entry(
        sha256="b" * 64,
        table_name="short_rows",
        path="artifact:bbbbbbbbbbbbbbbb",
        size=1,
        row_count=1,
    )

    sink.write_artifact_rows(
        schema,
        [["only_one_col"]],
        source_artifact_path="artifact:bbbbbbbbbbbbbbbb",
        source_artifact_sha256="b" * 64,
        catalog_entry=catalog_entry,
        replace_existing=False,
    )

    assert copied == [
        ("only_one_col", None, "artifact:bbbbbbbbbbbbbbbb", "b" * 64, 1)
    ]
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_prepare_typed_rows_coerces_present_bigint_and_preserves_missing_cell() -> None:
    """The list-producing path keeps coercion and missing-cell semantics aligned."""
    schema = TableSchema(
        table_name="typed_rows",
        columns=[ColumnSpec("ID", "id_field", PG_BIGINT)],
    )

    assert prepare_typed_rows(schema, [[], ["12"]]) == [[None], [12]]
