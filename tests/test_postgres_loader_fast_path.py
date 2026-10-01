import pytest
from mhtml_etl_gateway.schema_inference import ColumnSpec, TableSchema
from mhtml_etl_gateway.postgres_loader import prepare_typed_rows

def test_prepare_typed_rows_fast_path_branching():
    """Verify that perfect, ragged, and over-long rows are correctly padded/truncated."""
    schema = TableSchema(
        table_name="test_fast_path",
        columns=[
            ColumnSpec(source_name="c1", db_name="c1", pg_type="text"),
            ColumnSpec(source_name="c2", db_name="c2", pg_type="text"),
            ColumnSpec(source_name="c3", db_name="c3", pg_type="text"),
        ]
    )

    assert prepare_typed_rows(schema, [["a", "b", "c"]]) == [["a", "b", "c"]]
    assert prepare_typed_rows(schema, [["a", "b"]]) == [["a", "b", None]]
    assert prepare_typed_rows(schema, [[]]) == [[None, None, None]]
    assert prepare_typed_rows(schema, [["a", "b", "c", "d"]]) == [["a", "b", "c"]]
    assert prepare_typed_rows(schema, [[None, "b", None]]) == [["None", "b", "None"]]

def test_prepare_typed_rows_benchmark():
    """Benchmark the optimized fast-path logic against baseline bounds-checking overhead."""
    schema = TableSchema(
        table_name="test",
        columns=[
            ColumnSpec(source_name=f"col{i}", db_name=f"col{i}", pg_type="text")
            for i in range(10)
        ]
    )

    rows_perfect = [["val"] * 10 for _ in range(10_000)]
    rows_ragged = [["val"] * 8 for _ in range(10_000)]

    prepare_typed_rows(schema, rows_perfect)
    prepare_typed_rows(schema, rows_ragged)
