import time
from typing import Sequence, Any

class ExtractedTable:
    def __init__(self, headers, rows):
        self.headers = headers
        self.rows = rows

def rows_as_dicts_old(table: ExtractedTable) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in table.rows:
        out.append({h: row[i] if i < len(row) else "" for i, h in enumerate(table.headers)})
    return out

def rows_as_dicts_new(table: ExtractedTable) -> list[dict[str, str]]:
    headers = table.headers
    num_cols = len(headers)
    out: list[dict[str, str]] = []
    app = out.append
    for row in table.rows:
        row_len = len(row)
        app(
            dict(zip(headers, row))
            if row_len >= num_cols else
            dict(zip(headers, list(row) + [""] * (num_cols - row_len)))
        )
    return out


headers = [f"h_{i}" for i in range(50)]
rows = [["val"] * 50 for _ in range(100000)]
table = ExtractedTable(headers, rows)

start = time.time()
rows_as_dicts_old(table)
print("Old perfectly formed dicts:", time.time() - start)

start = time.time()
rows_as_dicts_new(table)
print("New perfectly formed dicts:", time.time() - start)

rows_ragged = [["val"] * 25 for _ in range(100000)]
table_ragged = ExtractedTable(headers, rows_ragged)

start = time.time()
rows_as_dicts_old(table_ragged)
print("Old ragged dicts:", time.time() - start)

start = time.time()
rows_as_dicts_new(table_ragged)
print("New ragged dicts:", time.time() - start)

def check_equality(headers, rows):
    table = ExtractedTable(headers, rows)
    old = rows_as_dicts_old(table)
    new = rows_as_dicts_new(table)
    assert old == new, f"Old: {old}, New: {new}"

check_equality(["a", "b"], [["1", "2"]])
check_equality(["a", "b"], [["1"]])
check_equality(["a", "b"], [[]])
check_equality(["a", "b"], [["1", "2", "3"]])
