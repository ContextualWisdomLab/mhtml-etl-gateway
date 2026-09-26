"""Regression contracts for native PostgreSQL loader cell values."""

from decimal import Decimal

from mhtml_etl_gateway.postgres_loader import prepare_typed_rows
from mhtml_etl_gateway.schema_inference import (
    PG_BIGINT,
    PG_NUMERIC,
    PG_TEXT,
    ColumnSpec,
    TableSchema,
    values_require_text,
)


def test_numeric_columns_reject_boolean_native_values() -> None:
    """Boolean cells must not pass PostgreSQL integer or numeric compatibility."""
    assert values_require_text(PG_BIGINT, [True]) is True
    assert values_require_text(PG_BIGINT, [False]) is True
    assert values_require_text(PG_NUMERIC, [True]) is True
    assert values_require_text(PG_NUMERIC, [False]) is True


def test_numeric_columns_preserve_supported_native_values() -> None:
    """Supported non-boolean numeric values remain compatible with typed columns."""
    assert values_require_text(PG_BIGINT, [7]) is False
    assert values_require_text(PG_NUMERIC, [7, Decimal("1.25"), 1.5]) is False


def test_prepare_typed_rows_preserves_native_values_and_fills_missing_cells() -> None:
    """Native cells stay native while absent trailing cells become ``None``."""
    schema = TableSchema(
        table_name="native_rows",
        columns=[
            ColumnSpec("COUNT", "count_field", PG_BIGINT),
            ColumnSpec("NOTE", "note_field", PG_TEXT),
        ],
    )

    assert prepare_typed_rows(schema, [[7, "hello"], [8]]) == [
        [7, "hello"],
        [8, None],
    ]
