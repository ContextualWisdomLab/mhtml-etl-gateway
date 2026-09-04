from __future__ import annotations

import pytest

from mhtml_etl_gateway.postgres_loader import LoadError, PsycopgSink
from mhtml_etl_gateway.schema_inference import PG_TEXT, ColumnSpec, TableSchema, to_table_name


def test_legacy_table_lookup_uses_one_bound_array_parameter() -> None:
    """Keep legacy table candidates out of SQL text and bind them as one array."""
    source_name = "x" * 80
    legacy_name = source_name[:63]
    schema = TableSchema(
        table_name=to_table_name(source_name),
        source_table_name=source_name,
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )
    sink = object.__new__(PsycopgSink)
    observed: list[tuple[str, object | None]] = []

    def fetchall(query, params=None):
        observed.append((query, params))
        return [(legacy_name,)]

    sink._fetchall = fetchall

    with pytest.raises(LoadError, match=r"legacy table requires explicit migration"):
        sink._reject_legacy_table_split(schema)

    assert len(observed) == 1
    query, params = observed[0]
    assert "AND table_name = ANY(%s)" in query
    assert legacy_name not in query
    assert isinstance(params, tuple)
    assert len(params) == 1
    assert isinstance(params[0], list)
    assert legacy_name in params[0]
    assert schema.table_name in params[0]
