## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-09-24 - Fix SQL injection potential in psycopg query
**Vulnerability:** String interpolation used in psycopg query to build `IN ({placeholders})` clause (flagged as B608 by bandit).
**Learning:** Even if interpolating `%s` placeholders, building query strings dynamically is poor practice and flagged by SAST tools.
**Prevention:** Use PostgreSQL's native `ANY(%s)` operator instead of `IN (...)` and pass the list of parameters in a single parameter `(list(query_names),)` which psycopg securely maps to a Postgres array.
