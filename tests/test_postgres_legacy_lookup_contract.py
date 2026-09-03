from __future__ import annotations

from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import PG_TEXT, ColumnSpec, TableSchema


def test_legacy_table_lookup_uses_static_any_query_with_one_list_parameter() -> None:
    """Keep collection binding static without turning candidate values into SQL text."""
    sink = object.__new__(PsycopgSink)
    observed: list[tuple[str, object]] = []

    def fetchall(query, params=None):
        observed.append((str(query), params))
        return []

    sink._fetchall = fetchall
    sink._reject_legacy_table_split(
        TableSchema(
            table_name="simple_table",
            columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
        )
    )

    assert observed == [
        (
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() "
            "AND table_name = ANY(%s)",
            (["simple", "simple_table"],),
        )
    ]
