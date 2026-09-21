## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-09-21 - [Fix SQL injection in postgres loader]
**Vulnerability:** String interpolation in SQL IN clauses creates a SQL Injection risk (Bandit B608).
**Learning:** We must not construct SQL queries with f-strings for parameters, even dynamically sized ones like IN clauses.
**Prevention:** Use psycopg3's native ANY(%s) array parameterization with list arguments.
