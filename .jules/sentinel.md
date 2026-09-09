## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-09-09 - [Bandit B608] SQL Injection Vector via f-strings in IN clauses
**Vulnerability:** Constructing `IN ({placeholders})` queries using f-strings and `.join()` triggers Bandit B608 (hardcoded_sql_expressions) as a possible SQL injection vector, even when parameters are bound.
**Learning:** Using psycopg3, the native parameterization for arrays should be used instead of manual string interpolation for IN clauses.
**Prevention:** Use `= ANY(%s)` instead of `IN ({placeholders})` and pass a Python list as the parameter, e.g., `(list(query_names),)`.
