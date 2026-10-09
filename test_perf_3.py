import time
from typing import Sequence, Any
from collections import namedtuple

Col = namedtuple("Col", ["pg_type"])
class TableSchema:
    def __init__(self, cols):
        self.columns = cols

def coerce_value(value: str, pg_type: str):
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    return s

def prepare_typed_rows_old(schema: TableSchema, rows: Sequence[Sequence[str]]) -> list[list[Any]]:
    prepared: list[list[Any]] = []
    for row in rows:
        prepared.append(
            [
                coerce_value(str(row[i]) if i < len(row) else "", col.pg_type)
                for i, col in enumerate(schema.columns)
            ]
        )
    return prepared

def prepare_typed_rows_new(schema: TableSchema, rows: Sequence[Sequence[str]]) -> list[list[Any]]:
    """Coerce string rows to Python types according to schema."""
    num_cols = len(schema.columns)
    col_types = [col.pg_type for col in schema.columns]

    prepared: list[list[Any]] = []
    app = prepared.append
    for row in rows:
        row_len = len(row)
        app(
            [
                coerce_value(row[i], col_types[i])
                for i in range(num_cols)
            ]
            if row_len >= num_cols
            else
            [
                coerce_value(row[i], col_types[i])
                for i in range(row_len)
            ] + [
                coerce_value("", col_types[i])
                for i in range(row_len, num_cols)
            ]
        )
    return prepared

def check_equality(schema, rows):
    old = prepare_typed_rows_old(schema, rows)
    new = prepare_typed_rows_new(schema, rows)
    assert old == new, f"Old: {old}, New: {new}"

cols = [Col(f"type_{i}") for i in range(5)]
schema = TableSchema(cols)
check_equality(schema, [["val"] * 5])
check_equality(schema, [["val"] * 2])
check_equality(schema, [[]])
