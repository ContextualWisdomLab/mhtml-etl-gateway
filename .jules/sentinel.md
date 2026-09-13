## 2026-09-13 - [SQL Injection Vector in PostgreSQL Loader]
**Vulnerability:** Possible SQL injection vector through string-based query construction when building `IN` clauses dynamically (`f"AND table_name IN ({placeholders})"`).
**Learning:** Even if the strings inserted are standard PostgreSQL bind markers (`%s`), using Python f-strings or string concatenation for `IN` clause generation obscures the query's security structure from static analysis tools like Bandit, leading to B608 violations.
**Prevention:** Always use PostgreSQL's native array adaptation `ANY(%s)` instead of dynamically building `IN (%s, %s, ...)` strings. Pass the variables wrapped in a standard Python list, which `psycopg` automatically adapts safely to the PostgreSQL array type.
