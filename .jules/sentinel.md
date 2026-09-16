## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-09-16 - [Fix string-based SQL query construction (B608)]
**Vulnerability:** String-based query construction. The `_reject_legacy_table_split` function in `postgres_loader.py` dynamically built an `IN ({placeholders})` clause using Python string formatting (`f"AND table_name IN ({placeholders})"`). While the injected strings were just literal `%s` markers rather than user data, this pattern triggers SAST (Bandit) B608 warnings and violates secure coding best practices by constructing SQL dynamically.
**Learning:** Using Python string interpolation (like f-strings or `.join()`) to build SQL strings, even just for generating placeholders, is a risky anti-pattern that creates brittle code and flags security scanners.
**Prevention:** Always use the database driver's native parameterization features. For PostgreSQL arrays in psycopg3+, use the `= ANY(%s)` operator and pass a Python list directly, rather than building dynamic `IN` clauses.
