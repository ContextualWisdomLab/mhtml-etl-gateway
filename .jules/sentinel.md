## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-11-07 - Fix SQL Injection in postgres_loader.py
**Vulnerability:** A SQL injection vulnerability (B608:hardcoded_sql_expressions) was identified by Bandit in `src/mhtml_etl_gateway/postgres_loader.py`. `f"AND table_name IN ({placeholders})"` was being used to construct an `IN` clause using string interpolation for placeholders.
**Learning:** Using `f-strings` or `.format()` to construct `IN (...)` query clauses in `psycopg3` can trigger security scanner alerts (like Bandit B608) and might be a SQL injection vector.
**Prevention:** Always use parameterized queries for dynamic values. In `psycopg3`, prefer utilizing PostgreSQL's native `ANY(%s)` syntax and passing a list parameter to adapt arrays natively instead of manually creating string placeholders.
