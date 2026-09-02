## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-05-01 - Prevent SQL Injection vectors from string-based queries in psycopg
**Vulnerability:** A static security scan identified a medium confidence SQL injection risk (Bandit B608) due to string interpolation for `IN ({placeholders})` queries. While parameterized with `%s`, string-building query components is an injection anti-pattern.
**Learning:** psycopg3 supports native adaptation for PostgreSQL arrays when a parameter is a Python list. Converting an `IN` check with dynamic placeholders to an `= ANY(%s)` check using a list wrapper safely resolves the vector and removes the static analysis warning.
**Prevention:** Avoid string interpolation (f-strings or `join`) to construct SQL query clauses for dynamic collections. Prefer psycopg3's native `ANY(%s)` array parameterization and supply a `(list(values),)` object.
