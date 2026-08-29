## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-08-29 - [Fix Bandit Medium SQL Injection Warning]
**Vulnerability:** Medium severity SQL Injection vulnerability (CWE-89) raised by Bandit (`B608:hardcoded_sql_expressions`) due to dynamic string formatting of an `IN` clause using f-strings and `.join("%s")` for array variables.
**Learning:** `psycopg` (v3+) natively adapts Python lists to PostgreSQL arrays, so we can replace dynamically constructed `IN` clauses (which trigger `B608` security warnings) with safe `= ANY(%s)` parameterized clauses.
**Prevention:** When parameterizing array matching in `psycopg`, use `column_name = ANY(%s)` and pass a Python list (wrapped in a tuple, e.g., `(list(values),)`) instead of concatenating placeholders into an `IN` clause.
