## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-10-11 - Fixed Bandit B608: Hardcoded SQL Expressions
**Vulnerability:** Found a hardcoded SQL expression in `src/mhtml_etl_gateway/postgres_loader.py` around line 384 where `f"AND table_name IN ({placeholders})"` was being used. Bandit threw a B608 issue indicating "Possible SQL injection vector through string-based query construction."
**Learning:** Using f-strings to format parameterized placeholders, even when passing safe identifiers, triggers Bandit B608 because it matches the AST pattern for string interpolation in SQL queries. In psycopg3, we can avoid string formatting entirely and prevent SQL injection risk natively by using `= ANY(%s)` instead of `IN ({placeholders})`, as psycopg3 handles array adaptation natively when we pass a list parameter.
**Prevention:** Always use `ANY(%s)` and pass a Python list to parameterize array queries with psycopg3, instead of using f-strings to build `IN (%s, %s, ...)` clauses.
