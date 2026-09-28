## 2024-03-08 - Fast Path Datetime Parsing
**Learning:** `datetime.fromisoformat()` in Python 3.11+ natively handles standard space-separated timestamps (like `2024-01-01 12:00:00`), but it also erroneously accepts pure dates (like `2024-01-01`). When using it to distinguish between DATE and TIMESTAMP data types via type inference, it requires an explicit check (like `if " " in s or "T" in s or "t" in s:`) to ensure time components actually exist before parsing it as a timestamp.
**Action:** When optimizing date/time parsing with `fromisoformat()` during type inference, always add explicit length/content checks to ensure correct type identification (preventing dates from being inferred as timestamps).

## 2024-08-10 - O(N) Loop Invariants & Generator Short-Circuiting in Large Data Set Processing
**Learning:** Checking constant conditions (`pg_type == ...`) inside a tight per-cell loop during validation causes massive overhead on large data streams (like PostgreSQL batch loads), as strings are compared for every cell repeatedly. Additionally, using list comprehensions (`[...]`) to slice data for validation forces memory allocation and entire iteration, preventing short-circuiting.
**Action:** When iterating over millions of items, hoist loop-invariant conditions (like type checks based on column types) outside the loop. Determine the expected validation type once, then run a simplified tight loop. Furthermore, use generator expressions (`(...)`) combined with short-circuiting evaluation instead of list comprehensions, so that validation can fail early and save both memory and CPU cycles.

## 2024-09-28 - Fast Path and Ragged Row Loop Optimization
**Learning:** When refactoring data processing loops to separate logic into 'fast paths' (for perfectly-formed rows) and 'slow paths' (for ragged rows), explicitly adding test cases for completely empty rows (e.g., `[[]]`), partially filled rows, and perfectly filled rows is critical to ensure all branch conditions are evaluated and 100% branch coverage is maintained.
**Action:** When implementing path-specific optimizations, always verify branch coverage with edge cases like empty sequences.
