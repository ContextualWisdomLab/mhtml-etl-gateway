"""Regression contracts for PostgreSQL row normalization and promotion checks."""

from __future__ import annotations

from typing import Any

import pytest

import mhtml_etl_gateway.postgres_loader as postgres_loader
from mhtml_etl_gateway.ingest_catalog import make_catalog_entry
from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import ColumnSpec, PG_BIGINT, TableSchema


class _CommitConnection:
    """Minimal transaction surface used by the row-boundary regression."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        """Record a successful transaction commit."""
        self.commits += 1

    def rollback(self) -> None:
        """Record a transaction rollback."""
        self.rollbacks += 1


def _bigint_schema() -> TableSchema:
    """Return the one-column schema shared by the normalization regressions."""
    return TableSchema(
        table_name="normalized_rows",
        columns=[ColumnSpec("ID", "id_field", PG_BIGINT)],
    )


def test_write_artifact_rows_uses_one_normalized_view_for_promotion_and_copy() -> None:
    """Promotion and COPY must observe the same normalized raw input value."""
    schema = _bigint_schema()
    entry = make_catalog_entry(
        sha256="a" * 64,
        table_name=schema.table_name,
        path="artifact:aaaaaaaaaaaaaaaa",
        size=4,
        row_count=1,
    )
    connection = _CommitConnection()
    sink = object.__new__(PsycopgSink)
    sink._conn = connection

    promotion_rows: list[list[Any]] = []
    copied_rows: list[tuple[Any, ...]] = []

    def capture_promotion(_schema: TableSchema, rows) -> list[str]:
        promotion_rows.extend([list(row) for row in rows])
        return []

    sink._columns_to_promote = capture_promotion
    sink._execute = lambda *_args, **_kwargs: None
    sink._copy_rows = lambda _query, rows: copied_rows.extend(tuple(row) for row in rows)

    assert sink.write_artifact_rows(
        schema,
        [[7]],
        source_artifact_path=entry.source_artifact_path,
        source_artifact_sha256=entry.source_artifact_sha256,
        catalog_entry=entry,
        replace_existing=False,
    ) == 1

    assert promotion_rows == [[7]]
    assert copied_rows == [(7, entry.source_artifact_path, entry.source_artifact_sha256, 1)]
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_columns_to_promote_never_recoerces_prepared_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prepared values must reach the promotion predicate without reparsing."""
    schema = _bigint_schema()
    sink = object.__new__(PsycopgSink)
    sink._fetchall = lambda *_args, **_kwargs: [("id_field", "bigint")]

    def fail_recoercion(*_args, **_kwargs):
        raise AssertionError("_columns_to_promote must not call coerce_value")

    monkeypatch.setattr(postgres_loader, "coerce_value", fail_recoercion)

    assert sink._columns_to_promote(schema, [[7]]) == []
