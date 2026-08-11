import time
from mhtml_etl_gateway.postgres_loader import prepare_typed_rows
from mhtml_etl_gateway.schema_inference import TableSchema, ColumnSpec, PG_BIGINT, PG_TEXT, PG_DATE, PG_NUMERIC, PG_BOOLEAN

def main():
    schema = TableSchema(
        table_name="test",
        columns=[
            ColumnSpec("A", "a", PG_BIGINT),
            ColumnSpec("B", "b", PG_TEXT),
            ColumnSpec("C", "c", PG_DATE),
            ColumnSpec("D", "d", PG_NUMERIC),
            ColumnSpec("E", "e", PG_BOOLEAN),
        ]
    )

    rows = [
        ["12345", "hello", "2024-01-01", "123.45", "true"]
        for _ in range(100000)
    ]

    start = time.time()
    res = prepare_typed_rows(schema, rows)
    end = time.time()

    print(f"Time taken: {end - start:.4f}s")

if __name__ == "__main__":
    main()
