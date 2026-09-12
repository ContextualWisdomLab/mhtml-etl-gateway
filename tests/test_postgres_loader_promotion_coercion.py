"""Regression coverage for promotion checks at the raw-row boundary."""

from __future__ import annotations

from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import PG_BIGINT, ColumnSpec, TableSchema


def _bigint_sink() -> PsycopgSink:
    sink = object.__new__(PsycopgSink)
    sink._fetchall = lambda query, params=None: [("value_field", "bigint")]
    return sink


def test_promotion_check_matches_copy_coercion_for_raw_numeric_strings() -> None:
    """Raw strings that COPY will coerce to BIGINT must not force TEXT promotion."""
    schema = TableSchema(
        table_name="typed_rows",
        columns=[ColumnSpec("VALUE", "value_field", PG_BIGINT)],
    )
    sink = _bigint_sink()

    assert sink._columns_to_promote(schema, [["1,000"], ["42"], [None], []]) == []
    assert sink._columns_to_promote(schema, [[1000], [42], [None], []]) == []
    assert sink._columns_to_promote(schema, [["not-an-integer"]]) == ["value_field"]
