## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-10-27 - [Fix SQL injection vector in postgres legacy table checks]
**Vulnerability:** Possible SQL injection vector through string-based query construction using f-strings for the `IN` clause `({placeholders})` in `_reject_legacy_table_split`. Bandit flagged this as `B608:hardcoded_sql_expressions`.
**Learning:** Using f-strings to format an `IN ({placeholders})` list can trigger static analysis tools as it looks like string manipulation for query building, even if the elements mapped to the placeholders are parameterized correctly.
**Prevention:** Use psycopg's native array parameterization `ANY(%s)` and pass the sequence as a list instead of constructing a string of format placeholders. This is not only safe from SQL injection, but cleanly bypasses Bandit B608 and improves code clarity.
