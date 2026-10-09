## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-10-09 - SQL Injection Risk via f-string IN clause
**Vulnerability:** Constructing `IN ({placeholders})` queries using f-strings triggered Bandit B608 (hardcoded SQL expressions) warning, potentially risking SQL injection.
**Learning:** Using string interpolation for `IN` clauses with standard `%s` placeholders trips static analysis because the query template isn't a constant literal.
**Prevention:** Use psycopg3's native `ANY(%s)` array parameterization instead. Pass the parameters as a Python list wrapped in a tuple: `(list(my_items),)`. This allows a constant literal query and safe parameter adaptation by the driver. Ensure tests mock cursor `_fetchall` handle the nested list format `observed[0][0]` instead of standard unpacked positional arguments.
