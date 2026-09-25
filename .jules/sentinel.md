## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-09-25 - [Fix B608 Hardcoded SQL Expression]
**Vulnerability:** Possible SQL injection vector through string-based query construction using f-strings for IN clauses.
**Learning:** Avoid string interpolation (f-strings) to construct IN ({placeholders}) clauses for SQL queries, as it triggers static security scanner (Bandit B608) warnings.
**Prevention:** Use psycopg3's native ANY(%s) array parameterization instead, wrapping the list in a tuple.
