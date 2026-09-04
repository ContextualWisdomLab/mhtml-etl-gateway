from __future__ import annotations

from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import PG_TEXT, ColumnSpec, TableSchema


def test_legacy_table_lookup_uses_one_postgres_array_parameter() -> None:
    """Legacy-table detection keeps SQL text fixed and binds candidate values as one array."""
    sink = object.__new__(PsycopgSink)
    observed: dict[str, object] = {}

    def fetchall(query, params=None):
        observed["query"] = str(query)
        observed["params"] = params
        return []

    sink._fetchall = fetchall
    schema = TableSchema(
        table_name="simple_table",
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )

    sink._reject_legacy_table_split(schema)

    assert "table_name = ANY(%s)" in observed["query"]
    assert "table_name IN (" not in observed["query"]
    assert observed["params"] == (["simple", "simple_table"],)
