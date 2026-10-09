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

    return [
        dict(zip(headers, row))
        if len(row) >= num_cols else
        dict(zip(headers, list(row) + [""] * (num_cols - len(row))))
        for row in table.rows
    ]

headers = [f"h_{i}" for i in range(50)]
rows = [["val"] * 50 for _ in range(100000)]
table = ExtractedTable(headers, rows)

start = time.time()
rows_as_dicts_old(table)
print("Old perfectly formed dicts:", time.time() - start)

start = time.time()
rows_as_dicts_new(table)
print("New perfectly formed dicts:", time.time() - start)
