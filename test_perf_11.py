import time
from typing import Sequence, Any

def prepare_typed_rows_old(schema, rows):
    prepared = []
    for row in rows:
        prepared.append(
            [
                str(row[i]) if i < len(row) else ""
                for i, col in enumerate(schema)
            ]
        )
    return prepared

def prepare_typed_rows_new(schema, rows):
    num_cols = len(schema)

    prepared = []
    app = prepared.append
    for row in rows:
        row_len = len(row)
        if row_len >= num_cols:
            app([
                row[i] if type(row[i]) is str else str(row[i])
                for i in range(num_cols)
            ])
        else:
            app(
                [
                    row[i] if type(row[i]) is str else str(row[i])
                    for i in range(row_len)
                ] + [
                    ""
                    for i in range(row_len, num_cols)
                ]
            )
    return prepared

def prepare_typed_rows_new2(schema, rows):
    num_cols = len(schema)

    return [
        [
            row[i] if type(row[i]) is str else str(row[i])
            for i in range(num_cols)
        ]
        if len(row) >= num_cols
        else
        [
            row[i] if type(row[i]) is str else str(row[i])
            for i in range(len(row))
        ] + ["" for _ in range(len(row), num_cols)]
        for row in rows
    ]

cols = [f"type_{i}" for i in range(50)]
rows = [["val"] * 50 for _ in range(100000)]

start = time.time()
prepare_typed_rows_old(cols, rows)
print("Old perfectly formed:", time.time() - start)

start = time.time()
prepare_typed_rows_new(cols, rows)
print("New perfectly formed:", time.time() - start)

start = time.time()
prepare_typed_rows_new2(cols, rows)
print("New2 perfectly formed:", time.time() - start)
