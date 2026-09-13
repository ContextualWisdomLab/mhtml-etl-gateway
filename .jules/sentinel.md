## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-09-13 - SQL Injection via Unparameterized `IN` Clause String Formatting
**Vulnerability:** Constructing `IN ({placeholders})` queries by manually formatting strings introduces critical SQL Injection risks (Bandit B608), even with internal logic constraints, when processing unsanitized dynamic identifiers.
**Learning:** Psycopg native `ANY(%s)` securely adapts Python lists into PostgreSQL arrays dynamically, eliminating the need for `IN(...)` placeholder formatting and bypassing the injection vector.
**Prevention:** Never use f-strings or string formatting to build dynamic query clauses. Use `table_name = ANY(%s)` and pass `(list(query_names),)` into `execute()` parameters.
