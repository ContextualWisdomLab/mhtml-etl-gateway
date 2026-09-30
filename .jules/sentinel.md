## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-05-20 - SQL Injection via f-strings in IN clauses
**Vulnerability:** Hardcoded SQL expression in IN clause
**Learning:** f-strings should not be used to build IN ({placeholders}) clauses. It triggered Bandit B608 and is a potential SQLi risk.
**Prevention:** Use native PostgreSQL ANY(%s) array parameterization with psycopg.
