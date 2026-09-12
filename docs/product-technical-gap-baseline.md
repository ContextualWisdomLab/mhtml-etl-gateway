# Product–Technical Gap Baseline

This document records product-facing technical gaps whose acceptance depends on executable repository evidence. The code, protected branch, pull-request diff, and exact-head checks remain authoritative when this document becomes stale.

## PostgreSQL legacy-table lookup

### Problem boundary

`PsycopgSink._reject_legacy_table_split()` protects migrations from silently creating a suffixed table beside an existing legacy table. The protected implementation generated only `%s` placeholder tokens in Python and supplied candidate table names separately as psycopg value parameters. No candidate table name was directly interpolated into SQL text, so Bandit B608 alone does not establish a reproduced SQL-injection vulnerability.

The candidate refactor uses PostgreSQL `= ANY(%s)` with one Python list parameter. PostgreSQL defines `ANY(array)` as comparison against each element of the array, and Psycopg 3 separates ordinary query text from bound parameters. The purpose of this change is therefore to make the query shape static and the value boundary easier to verify, not to claim remediation of an exploit that has not been reproduced.

### Domain and data invariants

- Legacy-table detection remains part of the PostgreSQL loading bounded context; no cross-service SQL or mutable sibling dependency is introduced.
- Candidate table names remain values, not SQL identifiers. A future dynamic identifier must use Psycopg SQL composition rather than value placeholders or Python string interpolation.
- The candidate set must include every legacy candidate plus the current schema table name with deterministic semantics.
- A lookup result matching a legacy candidate must still fail closed with `LoadError("legacy table requires explicit migration")` before schema mutation.
- Query-shape hardening must not change transaction boundaries, catalog idempotency, lineage fields, or table-name normalization.

### Current evidence and gap

PR #79 is the canonical repair lane. Test repair on descendant `71603d25285ca35cbd71e684dbe549bc7a7f5b1c` captures both SQL text and parameters, requires `table_name = ANY(%s)`, requires exactly one placeholder and one list-valued parameter, and requires both the legacy candidate and current schema table name. That descendant also rejects the generated `IN (` query shape.

The remaining source diff still contains formatter-only changes unrelated to the lookup. Those are not part of this gap and must be ordinary-forward restored to protected-base spelling before merge.

Exact-head hosted checks must be read from GitHub after the final content head settles; predecessor receipts are not promoted to a later commit identity.

### RED → GREEN acceptance

1. **RED:** the focused regression fails when `_reject_legacy_table_split()` returns to generated `IN (%s, ...)` query text or drops any expected candidate from the single bound array.
2. **GREEN:** the minimum production delta uses structurally static `table_name = ANY(%s)` with one bound candidate array while preserving legacy rejection semantics.
3. Full repository tests and owned statement/branch coverage remain at repository-required thresholds on the same exact head.
4. Bandit/SAST/Security and CodeQL are evaluated on that exact head. Scanner or workflow failures are root-caused; warnings are not suppressed to manufacture GREEN.
5. Current-head independent review has no unresolved valid finding. Model/bot review is supporting evidence, not self-approval.
6. Merge occurs only through normal protected governance. Any central CI defect is handed to its canonical owner with immutable repo/PR/head/base/run evidence rather than worked around in this repository.

### Release effect

This is a database-query refactor unless new exploit evidence establishes a security defect. Release notes must not describe it as a MEDIUM SQL-injection fix merely because a static analyzer classified the previous query construction pattern.

## Traceability

- PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row and array comparisons*. https://www.postgresql.org/docs/18/functions-comparisons.html
- Psycopg Team. (2026). *Psycopg 3 documentation: Cursor classes*. https://www.psycopg.org/psycopg3/docs/api/cursors.html
- Psycopg Team. (2026). *Psycopg 3 documentation: SQL string composition*. https://www.psycopg.org/psycopg3/docs/api/sql.html
- Repository evidence: `ContextualWisdomLab/mhtml-etl-gateway` PR #79, protected base `main@e3d21b0a44ab8430009160e4005df18351bf27c9`.
