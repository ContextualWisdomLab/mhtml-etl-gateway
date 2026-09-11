"""Regression coverage for PostgreSQL sink string-subclass coercion."""

from __future__ import annotations

from mhtml_etl_gateway.ingest_catalog import make_catalog_entry
from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import PG_BIGINT, ColumnSpec, TableSchema


class _StringCell(str):
    """Model parser/library values that preserve ``str`` semantics via a subtype."""


class _Transaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_write_artifact_rows_coerces_string_subclasses_before_copy() -> None:
    """String-like cells must follow schema coercion before PostgreSQL COPY."""
    sink = object.__new__(PsycopgSink)
    sink._conn = _Transaction()
    sink._columns_to_promote = lambda schema, rows: []
    sink._execute = lambda *args, **kwargs: None
    copied_rows: list[tuple[object, ...]] = []
    sink._copy_rows = lambda query, rows: copied_rows.extend(rows)

    schema = TableSchema(
        table_name="typed_rows",
        columns=[ColumnSpec("VALUE", "value_field", PG_BIGINT)],
    )
    catalog_entry = make_catalog_entry(
        sha256="a" * 64,
        table_name="typed_rows",
        path="artifact:aaaaaaaaaaaaaaaa",
        size=1,
        row_count=1,
    )

    assert sink.write_artifact_rows(
        schema,
        [[_StringCell("1,000")]],
        source_artifact_path="artifact:aaaaaaaaaaaaaaaa",
        source_artifact_sha256="a" * 64,
        catalog_entry=catalog_entry,
        replace_existing=False,
    ) == 1
    assert copied_rows == [
        (1000, "artifact:aaaaaaaaaaaaaaaa", "a" * 64, 1)
    ]
    assert sink._conn.commits == 1
    assert sink._conn.rollbacks == 0
