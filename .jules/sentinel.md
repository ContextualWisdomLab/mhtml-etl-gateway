## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-09-09 - PostgreSQL legacy-table lookup parameterization
**Finding:** The legacy-table query generated only `%s` placeholder tokens in Python and continued to pass every table name as a bound parameter. No user-controlled identifier or value was interpolated into the SQL text, so the prior implementation is not treated as a reproduced SQL-injection vulnerability merely because Bandit B608 flagged the f-string.
**Decision:** Psycopg 3 documents `= ANY(%s)` with a Python list as the native array-binding form for a collection of values. The lookup therefore uses `table_name = ANY(%s)` to keep the query text static and make the parameter boundary clearer to both readers and static analysis.
**Invariant:** Table names remain data parameters, never SQL identifiers or interpolated literals. Any future dynamic identifier must use Psycopg's SQL-composition API rather than value placeholders or string formatting.
