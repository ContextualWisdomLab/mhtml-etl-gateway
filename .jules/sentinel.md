## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-05-18 - Hardcoded SQL expression via String Formatting
**Vulnerability:** String interpolation (`f"AND table_name IN ({placeholders})"`) used to dynamically create `IN` clauses for Postgres queries creates a potential SQL injection vector, which static analysis (Bandit B608) flags.
**Learning:** Using `IN (%s, %s, ...)` built with string formatting is insecure and generally slower for variable-length inputs in Postgres.
**Prevention:** Use Postgres-native parameterization with the `ANY` operator: `= ANY(%s)`, passing the values securely as a Python list adapted to a Postgres array.
