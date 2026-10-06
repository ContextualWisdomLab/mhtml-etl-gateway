## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-05-18 - Fix SQL injection via string formatting
**Vulnerability:** Used f-strings to format `IN ({placeholders})` clause which can lead to SQL injection.
**Learning:** The bandit static analyzer flags `f-strings` in SQL execution blocks as a potential SQL injection vector (B608). `psycopg` natively supports `ANY(%s)` where you can pass a list in the params parameter to handle PostgreSQL array queries.
**Prevention:** Avoid string formatting for parameterization in SQL statements; always use list mappings for `ANY(%s)` with `psycopg` to prevent SQL injection vulnerabilities.
