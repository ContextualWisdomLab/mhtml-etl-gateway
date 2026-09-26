## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-09-26 - [Fix SQL injection vulnerability in IN clause]
**Vulnerability:** A Bandit B608 medium severity warning indicated a possible SQL injection vector through string-based query construction. An f-string was used to construct an `IN ({placeholders})` clause instead of parameterizing it.
**Learning:** Using f-strings to construct `IN (...)` clauses for SQL queries triggers static security scanner (Bandit B608) warnings and introduces a possible SQL injection risk.
**Prevention:** Avoid string interpolation (f-strings) to construct `IN` clauses. Instead, use psycopg3's native `ANY(%s)` array parameterization by passing a Python `list` to correctly adapt to PostgreSQL arrays.
