## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-08-26 - [Fix SQL injection in postgres_loader table check]
**Vulnerability:** Possible SQL injection vector through string-based query construction in `PsycopgSink._reject_legacy_table_split` when dynamically building an `IN ({placeholders})` clause using an f-string.
**Learning:** Dynamically interpolating the query string, even just for placeholders like `", ".join("%s" for _ in items)`, triggers static analysis warnings (e.g., Bandit `B608:hardcoded_sql_expressions`) and introduces unnecessary risk when parameterizing variable-length IN clauses.
**Prevention:** When parameterizing `ANY(%s)` queries with `psycopg` (v3+), wrap the parameter in a Python `list` (e.g., `(list(my_items),)`) rather than a `tuple` or dynamically generated string of placeholders. `psycopg` natively adapts Python lists to PostgreSQL arrays, making queries safer and simpler.
