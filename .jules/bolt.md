## 2026-02-12 - [Tight Loop List Comprehension Performance]
**Learning:** In CPython, list comprehensions are heavily optimized in C and generally outperform manual `for` loops with pre-allocated arrays (e.g., `[None] * N`) and index assignment. When optimizing loop bottlenecks, retain list comprehensions where possible. Optimize them by hoisting invariant lookups (like iterating over a cached list) and caching properties like `len(row)` outside the comprehension, rather than dismantling the comprehension into a manual bounds-checking loop.
**Action:** Retain list comprehensions for high-performance loops. Use `if (row_len := len(row)) >= c` to pre-evaluate sequence lengths outside inner loop branches.

## 2026-02-13 - [Truthiness vs Explicit Checks in Tight Loops]
**Learning:** In Python tight loops, leveraging implicit truthiness (e.g., `if v and str(v).strip()`) evaluates significantly faster than explicit type and value checks (e.g., `if v is not None and str(v).strip() != ''`).
**Action:** Favor truthiness checks for conditional evaluation inside fast ingestion loops where `None` and empty strings share semantic equivalence.

## 2026-03-01 - [Fast Dictionary Initialization in Hot Loops]
**Learning:** When constructing repetitive dictionaries in hot data ingestion loops, explicitly initializing keys directly as a dictionary (e.g., `{ "key": val }`) is significantly faster than initializing an empty dict and assigning items or using `dict.copy()` on a pre-allocated base record.
**Action:** When building rows for PostgreSQL, combine standard dictionary comprehension for varying schema columns with `.update(base_record)` for static lineage metadata.

## 2026-09-19 - [Optimize Dictionary and Row parsing using Hoisting]
**Learning:** `prepare_typed_rows` and `_build_row_records` inside `mhtml_etl_gateway/postgres_loader.py` are critical row processing logic. Moving the length check outside inner list comprehension loops (`len(row)`) and flattening out the columns parameter cache outside the row loop significantly speeds them up. Using the Walrus operator helps, but list comprehensions combined with an `if (row_len := len(row)) >= num_cols` check branch perfectly to avoid checking index bounds per-column for correctly formed rows.
**Action:** Apply this transformation logic to `.mhtml_etl_gateway/postgres_loader.py` to boost ingestion loops.
