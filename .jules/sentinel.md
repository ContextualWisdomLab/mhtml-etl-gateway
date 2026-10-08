## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-10-08 - Fixed SQL Injection Vector in Postgres Loader
**Vulnerability:** String interpolation (f-string) was used to construct an `IN ({placeholders})` clause in `_reject_legacy_table_split`, which triggers a Bandit B608 warning and is a possible SQL injection vector (even though inputs were partially controlled, it violates strict secure coding practices).
**Learning:** `psycopg` natively adapts Python lists to PostgreSQL arrays, so string interpolation for `IN` clauses is unnecessary and insecure.
**Prevention:** Use `psycopg`'s native array parameterization via `ANY(%s)` and pass the parameters wrapped in a list, like `(list(query_names),)`.
