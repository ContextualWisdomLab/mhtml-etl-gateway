## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-05-24 - Avoid f-strings for SQL IN clauses
**Vulnerability:** SQL injection vector identified when using f-strings and placeholders (`IN ({placeholders})`) to construct SQL queries, even when iterating over internally generated values.
**Learning:** Python string formatting can lead to SQL injection vulnerabilities and trigger security scanners (Bandit B608). Wrapping parameters explicitly or generating strings is less secure and less efficient.
**Prevention:** Always use `psycopg`'s native array parameterization `ANY(%s)` and pass a Python list (e.g., `(list(items),)`) for PostgreSQL `IN` clauses to ensure safe parameter adaptation.
