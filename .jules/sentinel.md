## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-08-27 - [Fix SQL injection vector via string formatting]
**Vulnerability:** Possible SQL injection vector via string formatting for IN clauses in postgres_loader.py (`f"AND table_name IN ({placeholders})"`).
**Learning:** Even though the placeholders are properly parameterized using `psycopg3` syntax later, dynamically generating the SQL string itself (via string interpolation of the placeholders) can be flagged by security scanners (e.g. Bandit) as a vector for SQL injection, and is a less ideal pattern.
**Prevention:** Use static query parameterization by replacing `IN` with `ANY(%s)` and passing a Python list via `(list(items),)`, which `psycopg` safely adapts to a PostgreSQL array without dynamically mutating the base query string.
