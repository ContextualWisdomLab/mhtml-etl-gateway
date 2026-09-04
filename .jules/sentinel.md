## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-09-04 - [Fix] SQL Injection vector due to string-based query construction
**Vulnerability:** Constructing SQL strings using `IN ({placeholders})` and Python string formatting triggered bandit B608 for a possible SQL injection vector, even if variables didn't originate from user input immediately.
**Learning:** Using `ANY(%s)` and passing `(list(params),)` natively leverages psycopg3 parameterization for array checks instead of dynamic string building.
**Prevention:** Avoid dynamic query constructions for lists, using PostgreSQL native `ANY(%s)` array parameters where applicable.
