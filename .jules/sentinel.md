## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-09-06 - [Fix SQL Injection risk in string-based IN query construction]
**Vulnerability:** Possible SQL injection vector (Bandit B608). The code dynamically formatted an `IN ({placeholders})` clause in `src/mhtml_etl_gateway/postgres_loader.py` using a Python f-string.
**Learning:** String interpolation, even when just constructing placeholders for parameterized variables, triggers security scanners and is less robust than native DBAPI array adaptations.
**Prevention:** Always use `ANY(%s)` and pass `(list(parameters),)` when querying with dynamic lists in psycopg3 to avoid f-strings and safely leverage native Postgres arrays.
