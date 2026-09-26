import pytest
from dataclasses import dataclass
from mhtml_etl_gateway.postgres_loader import InMemorySink, LoadError, prepare_typed_rows, coerce_value
from mhtml_etl_gateway.schema_inference import TableSchema, ColumnSpec, PG_BIGINT
from typing import Sequence, Any

class Text(str):
    pass

def test_str_subclass_coercion_write():
    schema = TableSchema(
        table_name="test_table_name",
        columns=[
            ColumnSpec(source_name="col_one", db_name="col_one", pg_type=PG_BIGINT),
        ],
    )
    val = Text(" 123 ")
    rows = [[val]]

    sha = "a" * 64
    from mhtml_etl_gateway.lineage import artifact_reference
    path = artifact_reference(sha)

    from mhtml_etl_gateway.postgres_loader import make_catalog_entry
    entry = make_catalog_entry(
        sha256=sha,
        table_name="test_table_name",
        path=path,
        size=10,
        row_count=1,
        status="loaded",
    )

    from mhtml_etl_gateway.postgres_loader import load_table
    sink = InMemorySink()
    sink.ensure_catalog()
    # Mock some existing table columns to trigger promotion check
    sink.ensure_table(schema)
    # the load_table method calls ensure_table, check promotion, etc...
    # we can't test actual DB promotion without PsycopgSink, but we can test
    # prepare_typed_rows to ensure strings and subclasses don't get stringified
    res = load_table(
        schema=schema,
        rows=rows,
        sink=sink,
        source_artifact_path=path,
        source_artifact_sha256=sha,
    )
    assert sink.rows["test_table_name"][0]["col_one"] == 123
