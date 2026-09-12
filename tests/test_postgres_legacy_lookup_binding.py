from __future__ import annotations

import pytest

from mhtml_etl_gateway.postgres_loader import LoadError, PsycopgSink
from mhtml_etl_gateway.schema_inference import (
    PG_TEXT,
    ColumnSpec,
    TableSchema,
    to_table_name,
)


def test_legacy_table_lookup_uses_one_postgres_array_parameter() -> None:
    """Legacy lookup keeps exact SQL fixed and binds candidates as one array value."""
    sink = object.__new__(PsycopgSink)
    observed: list[tuple[str, object]] = []

    def fetchall(query, params=None):
        observed.append((str(query), params))
        return []

    sink._fetchall = fetchall
    schema = TableSchema(
        table_name="simple_table",
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )

    sink._reject_legacy_table_split(schema)

    assert observed == [
        (
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() "
            "AND table_name = ANY(%s)",
            (["simple", "simple_table"],),
        )
    ]


def test_legacy_table_lookup_keeps_boundary_candidates_out_of_sql_text() -> None:
    """Long legacy/current names remain bound values and preserve fail-closed migration."""
    source_name = "x" * 80
    legacy_name = source_name[:63]
    schema = TableSchema(
        table_name=to_table_name(source_name),
        source_table_name=source_name,
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )
    sink = object.__new__(PsycopgSink)
    observed: list[tuple[str, object]] = []

    def fetchall(query, params=None):
        observed.append((str(query), params))
        return [(legacy_name,)]

    sink._fetchall = fetchall

    with pytest.raises(LoadError, match=r"legacy table requires explicit migration"):
        sink._reject_legacy_table_split(schema)

    assert len(observed) == 1
    query, params = observed[0]
    assert query.endswith("AND table_name = ANY(%s)")
    assert legacy_name not in query
    assert schema.table_name not in query
    assert isinstance(params, tuple)
    assert len(params) == 1
    assert isinstance(params[0], list)
    assert legacy_name in params[0]
    assert schema.table_name in params[0]
