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
    num_cols = len(schema.columns)
    col_types = [col.pg_type for col in schema.columns]

    prepared: list[list[Any]] = []
    app = prepared.append
    for row in rows:
        row_len = len(row)
        if row_len >= num_cols:
            app([
                coerce_value(row[i], col_types[i])
                for i in range(num_cols)
            ])
        else:
            app(
                [
                    coerce_value(row[i], col_types[i])
                    for i in range(row_len)
                ] + [
                    coerce_value("", col_types[i])
                    for i in range(row_len, num_cols)
                ]
            )
    return prepared


cols = [Col(f"type_{i}") for i in range(50)]
schema = TableSchema(cols)
# 100,000 perfectly formed rows
rows = [["val"] * 50 for _ in range(100000)]

# warmup
prepare_typed_rows_old(schema, rows[:100])
prepare_typed_rows_new(schema, rows[:100])

start = time.time()
prepare_typed_rows_old(schema, rows)
print("Old perfectly formed:", time.time() - start)

start = time.time()
prepare_typed_rows_new(schema, rows)
print("New perfectly formed:", time.time() - start)

# 100,000 ragged rows
rows_ragged = [["val"] * 25 for _ in range(100000)]
start = time.time()
prepare_typed_rows_old(schema, rows_ragged)
print("Old ragged:", time.time() - start)

start = time.time()
prepare_typed_rows_new(schema, rows_ragged)
print("New ragged:", time.time() - start)
