## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-09-07 - [Fix SQL injection vector in postgres_loader]
**Vulnerability:** Constructing SQL `IN` clauses dynamically with python f-strings `f"IN ({placeholders})"` creates a potential SQL injection vector, and it's flagged by `bandit` as `B608`.
**Learning:** Even when `placeholders` just contains a list of `%s` tokens correctly escaped later, the explicit formatting pattern is an anti-pattern. `psycopg` has native capabilities for array parameterization that we should leverage.
**Prevention:** Always use `ANY(%s)` combined with a Python list `(list(my_items),)` rather than explicitly formatting `%s` markers for `IN` clauses.
