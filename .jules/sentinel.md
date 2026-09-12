## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-05-18 - [Fix SQL Injection Vulnerability in IN Clause]
**Vulnerability:** Possible SQL injection vector through string-based query construction (Bandit B608). The `_reject_legacy_table_split` function was using string interpolation (`f"AND table_name IN ({placeholders})"`) to construct an `IN` clause dynamically based on user-derived table names.
**Learning:** String interpolation should never be used to construct SQL queries, even for dynamic `IN` clauses, as it creates an SQL injection risk and triggers static security scanners.
**Prevention:** Use native parameterized query features provided by the database driver. For psycopg3, replace dynamically built `IN ({placeholders})` clauses with parameter-bound `= ANY(%s)` using native Python list adaptation (`(list_names,)`).
