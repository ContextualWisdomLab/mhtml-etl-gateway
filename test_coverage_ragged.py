from mhtml_etl_gateway.postgres_loader import prepare_typed_rows
from mhtml_etl_gateway.schema_inference import TableSchema, ColumnSpec

def test_ragged():
    schema = TableSchema(
        table_name="test",
        columns=[
            ColumnSpec(source_name="col1", db_name="col1", pg_type="TEXT"),
            ColumnSpec(source_name="col2", db_name="col2", pg_type="TEXT"),
        ]
    )
    # Ragged row
    prepare_typed_rows(schema, [["val1"]])

if __name__ == "__main__":
    test_ragged()
