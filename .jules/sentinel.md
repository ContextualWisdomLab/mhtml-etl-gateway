## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-05-18 - [Fix Hardcoded SQL Expressions]
**Vulnerability:** Possible SQL injection vector through string-based query construction (Bandit B608). The IN clause was constructed using string formatting.
**Learning:** Avoid string interpolation or f-strings for SQL queries to construct IN clauses. Using psycopg3's native ANY(%s) array parameterization is secure and performant. When parameterizing ANY(%s) queries with psycopg, wrap the parameter in a Python list (e.g., (list(items),)) rather than a tuple.
**Prevention:** Use list parameters and ANY(%s) instead of string formatting for dynamic IN clauses.
