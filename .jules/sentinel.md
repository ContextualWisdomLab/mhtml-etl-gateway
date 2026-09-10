## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.

## 2024-09-10 - Parameterizing SQL `IN` Clauses
**Vulnerability:** Constructing `IN` clauses via string interpolation (e.g., `f"IN ({placeholders})"`) is flagged by Bandit (B608) as a potential SQL injection vector, even if the inputs are validated and placeholders are correctly bound later.
**Learning:** Security scanners expect strict, recognizable parameterization patterns without format strings.
**Prevention:** For list lookups in psycopg3, use the PostgreSQL `ANY(%s)` operator and pass the parameters as a Python list wrapped in a tuple `(list(values),)`. This natively adapts the Python list to a PostgreSQL array in a scanner-safe way.
