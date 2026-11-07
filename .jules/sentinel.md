## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-05-18 - [Fix SQL Injection Risk in Table Lookup]
**Vulnerability:** Possible SQL injection vector through string-based query construction using f-strings for `IN ({placeholders})` clause in `postgres_loader.py`.
**Learning:** Using f-strings to format a list of placeholders into a SQL `IN` clause triggers static security scanner (Bandit B608) warnings and is prone to errors, even if the dynamic parameters are bind variables.
**Prevention:** Use psycopg3's native `ANY(%s)` array parameterization, wrapping the parameter in a Python `list` instead. Also, ensure tests mocking `_fetchall` handle the tuple containing the list appropriately.
