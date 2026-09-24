## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-05-18 - [Fix SQL Injection vulnerability in postgres_loader]
**Vulnerability:** A potential SQL injection vector existed due to constructing an `IN (...)` clause using Python f-strings and `.join()` instead of native array parameters.
**Learning:** String interpolation for SQL parameters triggers Bandit (B608) and is unsafe. While the source identifiers were somewhat sanitized by `TableSchema.ddl()` previously, any bug there could lead to injection. psycopg natively supports `ANY(%s)` when passing Python lists.
**Prevention:** Avoid string interpolation for SQL queries. Use psycopg native array parameterization `ANY(%s)` with a Python `list` parameter.
