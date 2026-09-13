import psycopg

from mhtml_etl_gateway.ingest_catalog import CatalogEntry
from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import (
    PG_BIGINT,
    PG_TEXT,
    ColumnSpec,
    TableSchema,
)


class DummyConn:
    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, q, *args):
        pass

    def commit(self):
        pass

    def copy(self, sql):
        return self

    def write_row(self, row):
        pass

    def rollback(self):
        pass


class StringCell(str):
    """String-like source cell used to preserve the public coercion contract."""


def _catalog_entry(*, row_count: int) -> CatalogEntry:
    return CatalogEntry(
        source_artifact_sha256="sha256",
        table_name="mhtml_test_table",
        source_artifact_path="path",
        source_artifact_size=None,
        row_count=row_count,
        status="loaded",
        loaded_at=None,
    )


def _sink(monkeypatch) -> PsycopgSink:
    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: DummyConn())
    sink = PsycopgSink("dummy")
    sink._fetchall = lambda *args: []
    sink._execute = lambda *args: None
    return sink


def test_adapted_rows_coverage(monkeypatch):
    schema = TableSchema(
        table_name="mhtml_test_table",
        columns=[
            ColumnSpec(source_name="col_a", db_name="col_a", pg_type=PG_TEXT),
            ColumnSpec(source_name="col_b", db_name="col_b", pg_type=PG_TEXT),
        ],
    )
    rows = [["val1"], [123, 456]]
    captured: list[tuple[object, ...]] = []
    sink = _sink(monkeypatch)
    sink._copy_rows = lambda _sql, rows_iter: captured.extend(rows_iter)

    result = sink.write_artifact_rows(
        schema=schema,
        rows=rows,
        source_artifact_path="path",
        source_artifact_sha256="sha256",
        catalog_entry=_catalog_entry(row_count=2),
        replace_existing=False,
    )

    assert result == 2
    assert captured == [
        ("val1", None, "path", "sha256", 1),
        (123, 456, "path", "sha256", 2),
    ]


def test_adapted_rows_coerces_string_subclasses(monkeypatch):
    """Optimization must preserve the prior isinstance(str) coercion boundary."""
    schema = TableSchema(
        table_name="mhtml_test_table",
        columns=[
            ColumnSpec(source_name="item_count", db_name="item_count", pg_type=PG_BIGINT),
        ],
    )
    rows = [[StringCell("41")]]
    captured: list[tuple[object, ...]] = []
    sink = _sink(monkeypatch)
    sink._columns_to_promote = lambda *_args: []
    sink._copy_rows = lambda _sql, rows_iter: captured.extend(rows_iter)

    result = sink.write_artifact_rows(
        schema=schema,
        rows=rows,
        source_artifact_path="path",
        source_artifact_sha256="sha256",
        catalog_entry=_catalog_entry(row_count=1),
        replace_existing=False,
    )

    assert result == 1
    assert captured[0][0] == 41
    assert type(captured[0][0]) is int
