## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2026-10-07 - SQL Injection Risk via String Interpolation in psycopg3
**Vulnerability:** Constructing IN ({placeholders}) clauses using string interpolation (f-strings) in psycopg3 triggered Bandit B608 due to potential SQL injection risk, even when placeholders were simply `%s`.
**Learning:** Static analysis tools like Bandit flag any string interpolation in SQL queries as unsafe.
**Prevention:** Use psycopg3's native ANY(%s) array parameterization by passing a Python list, which cleanly avoids string interpolation and provides safe native array mapping.
