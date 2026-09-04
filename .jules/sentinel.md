## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-08-28 - [Fix potential SQL injection vector in postgres_loader.py]
**Vulnerability:** A `B608:hardcoded_sql_expressions` vulnerability was identified in `src/mhtml_etl_gateway/postgres_loader.py`. The query construction used string formatting `f"AND table_name IN ({placeholders})"` to build an `IN` clause dynamically. Although the inputs were likely safe identifiers, string formatting in queries is a poor security practice and a potential injection vector if identifier validation were to fail or change.
**Learning:** Using string formatting for dynamic `IN` clauses bypasses standard database parameterisation protections. When using PostgreSQL (via psycopg), the `IN (...)` pattern with dynamic lists of placeholders can be cleanly replaced with `ANY(%s)`.
**Prevention:** Avoid string formatting for SQL queries entirely. Use `ANY(%s)` and pass a Python list (e.g. `(list(query_names),)`) to parametrise dynamic array inputs safely with `psycopg`.
