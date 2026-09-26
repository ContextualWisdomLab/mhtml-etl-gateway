## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2026-09-25 - [Fix B608 Hardcoded SQL Expression]
**Finding:** Bandit B608 flagged an f-string that interpolated only internally generated `%s` placeholders; the table names themselves remained bound parameters, so current evidence does not establish an exploitable SQL-injection path.
**Learning:** Even safe placeholder-only SQL interpolation is difficult for static analysis and future maintainers to distinguish from value interpolation.
**Prevention:** Use psycopg3's native `ANY(%s)` array parameterization, passing the candidate-name list as one bound value, so query structure stays constant.
