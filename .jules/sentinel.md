## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-05-18 - [Fix Hardcoded SQL Expression vulnerability]
**Vulnerability:** Possible SQL injection vector through string-based query construction using `f"AND table_name IN ({placeholders})"`. Even though the values were parameterized, bandit flags any usage of f-strings or string concatenation in queries as risky.
**Learning:** We must not use string interpolation or concatenation when building SQL queries, even for placeholders. psycopg allows native adaptation of Python lists to PostgreSQL arrays.
**Prevention:** Instead of generating `IN (%s, %s, ...)` through string manipulation, use `= ANY(%s)` and pass the array of values as a single parameter like `(list(query_names),)`.
