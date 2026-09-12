from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import TableSchema, ColumnSpec, PG_TEXT
import psycopg


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


def test_adapted_rows_coverage(monkeypatch):
    schema = TableSchema(
        table_name="mhtml_test_table",
        columns=[
            ColumnSpec(source_name="col_a", db_name="col_a", pg_type=PG_TEXT),
            ColumnSpec(source_name="col_b", db_name="col_b", pg_type=PG_TEXT),
        ],
    )
    rows = [["val1"], [123, 456]]
    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: DummyConn())
    sink = PsycopgSink("dummy")
    sink._fetchall = lambda *args: []
    sink._execute = lambda *args: None
    sink._copy_rows = lambda sql, rows_iter: list(rows_iter)

    from mhtml_etl_gateway.ingest_catalog import CatalogEntry

    entry = CatalogEntry(
        source_artifact_sha256="sha256",
        table_name="mhtml_test_table",
        source_artifact_path="path",
        source_artifact_size=None,
        row_count=2,
        status="loaded",
        loaded_at=None,
    )

    sink.write_artifact_rows(
        schema=schema,
        rows=rows,
        source_artifact_path="path",
        source_artifact_sha256="sha256",
        catalog_entry=entry,
        replace_existing=False,
    )
