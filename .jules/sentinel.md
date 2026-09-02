## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-09-01 - SQL Query Construction in Legacy Table Name Checks
**Vulnerability:** Bandit B608 flagged the dynamically constructed `IN ({placeholders})` query in `_reject_legacy_table_split`. The exact implementation interpolated only generated `%s` placeholder tokens and still bound every table-name value separately, so the reviewed code did not expose a value-injection path; the concern was the dynamic-query pattern and its regression risk.
**Learning:** Psycopg 3 adapts Python lists to PostgreSQL arrays and documents `= ANY(%s)` with a list as the supported way to bind a collection to a membership predicate.
**Prevention:** Keep the SQL text static and pass the candidate table names as one bound list, e.g. `= ANY(%s)` with `(list(values),)`. Do not interpolate data values into SQL text.
