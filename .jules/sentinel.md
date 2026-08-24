## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-08-24 - [Fix False Positive SQL Injection in PostgreSQL Loader]
**Vulnerability:** A linter incorrectly identified `f"AND table_name IN ({placeholders})"` as a SQL injection vector (`B608:hardcoded_sql_expressions`) in `postgres_loader.py`.
**Learning:** While the query was safely parameterized using `psycopg` via `placeholders = ", ".join("%s" for _ in query_names)` and passing `query_names` to `_fetchall`, linters and security scanners often flag string-interpolated `IN` clauses as hardcoded SQL expressions.
**Prevention:** Replaced the string-interpolated `IN` clause with PostgreSQL's safer `= ANY(%s)` array comparison pattern. By passing a list of values (`(list(query_names),)`), `psycopg` properly translates it into an array binding, avoiding linter warnings and maintaining safe query parameterization.
