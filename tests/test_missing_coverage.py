import datetime
import pytest
from mhtml_etl_gateway.postgres_loader import PsycopgSink, TableSchema
from mhtml_etl_gateway.schema_inference import PG_TEXT, ColumnSpec, PG_BIGINT

def test_columns_to_promote_null(monkeypatch):
    schema = TableSchema("test_table", [ColumnSpec("Col 1", "col_1", PG_BIGINT)])
    # Mock sink so we don't need real DB connection
    sink = PsycopgSink.__new__(PsycopgSink)
    sink._fetchall = lambda query, params: [("col_1", "bigint")]

    rows = [[None], []]

    to_promote = sink._columns_to_promote(schema, rows)
    assert to_promote == []
