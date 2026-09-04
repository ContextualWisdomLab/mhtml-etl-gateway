## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-08-24 - [PostgreSQL legacy-table lookup scanner false positive]
**Finding:** Bandit B608 flagged the dynamically assembled placeholder list in `PsycopgSink._reject_legacy_table_split`. The existing query binds every table-name value separately, so this evidence does not establish a SQL injection vulnerability; it does expose avoidable dynamic SQL text that static analysis cannot prove safe.
**Learning:** Psycopg 3 adapts a Python `list` to a PostgreSQL array and documents `= ANY(%s)` as the parameterized form for matching a list of candidate values. A fixed query shape is easier to audit and avoids constructing SQL text solely to vary placeholder count.
**Prevention:** Keep values bound and use `table_name = ANY(%s)` with one list parameter. Preserve deterministic candidate ordering and add a regression test that asserts the fixed query shape and parameter envelope before claiming the scanner finding repaired.
