## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-09-22 - [Fix SQL Injection in query construction]
**Vulnerability:** Found a B608 medium severity possible SQL injection vector via string interpolation.
**Learning:** Constructing IN clauses using f-strings with a joined list of string parameters causes a Bandit B608 vulnerability because it bypasses driver-level parameterization.
**Prevention:** Use psycopg's native ANY(%s) with lists of values instead of dynamically constructed IN clauses.
