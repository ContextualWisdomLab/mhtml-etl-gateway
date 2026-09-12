# Product–Technical Gap Baseline

This document records product-facing technical gaps whose acceptance depends on executable repository evidence. The code, protected branch, pull-request diff, and exact-head checks remain authoritative when this document becomes stale.

## PostgreSQL legacy-table lookup

### Problem boundary

`PsycopgSink._reject_legacy_table_split()` protects migrations from silently creating a suffixed table beside an existing legacy table. The protected implementation generated only `%s` placeholder tokens in Python and supplied candidate table names separately as psycopg value parameters. No candidate table name was directly interpolated into SQL text, so Bandit B608 alone does not establish a reproduced SQL-injection vulnerability.

The candidate refactor uses PostgreSQL `= ANY(%s)` with one Python list parameter. PostgreSQL defines `ANY(array)` as comparison against each element of the array. Psycopg 3 documents Python-list adaptation to PostgreSQL arrays and recommends `= ANY(%s)` for collection membership, while its cursor API keeps ordinary query text and bound values separate. The purpose of this change is therefore to make the query shape static and the value boundary easier to verify, not to claim remediation of an exploit that has not been reproduced.

### Domain and data invariants

- Legacy-table detection remains part of the PostgreSQL loading bounded context; no cross-service SQL or mutable sibling dependency is introduced.
- Candidate table names remain values, not SQL identifiers. A future dynamic identifier must use Psycopg SQL composition rather than value placeholders or Python string interpolation.
- The candidate set must include every legacy candidate plus the current schema table name with deterministic semantics.
- A lookup result matching a legacy candidate must still fail closed with `LoadError("legacy table requires explicit migration")` before schema mutation.
- Query-shape hardening must not change transaction boundaries, catalog idempotency, lineage fields, or table-name normalization.

### Decision and rejected alternatives

Use one fixed predicate, `table_name = ANY(%s)`, and pass the deterministic candidate set as one Python list inside the DB-API parameter sequence.

Rejected alternatives:

- Keeping generated `IN (%s, ...)` text and suppressing B608 leaves unnecessary variable SQL shape and weaker auditability even though the values remain bound.
- Interpolating candidate values into SQL would cross the value-binding boundary and create the injection risk that the predecessor did not have.
- Treating a tuple as the PostgreSQL array value is not the documented Psycopg collection-adaptation contract used here; the bound collection is a Python list.
- Closing a documentation-only predecessor without carrying its executable contract, traceability, and changelog delta would lose valid evidence. Those deltas are consolidated into the canonical lane instead.

### Current evidence and gap

PR #79 is the canonical repair lane. Test repair on descendant `71603d25285ca35cbd71e684dbe549bc7a7f5b1c` captures both SQL text and parameters, requires `table_name = ANY(%s)`, exactly one placeholder and one list-valued parameter, and requires both the legacy candidate and current schema table name. That descendant also rejects the generated `IN (` query shape. A second focused contract, consolidated from predecessor #42, pins `simple` / `simple_table` to the exact one-list envelope `(["simple", "simple_table"],)`.

`CHANGELOG.md` now records the unreleased fixed-query-shape change. The remaining source diff still contains formatter-only changes unrelated to the lookup. Those are not part of this gap and must be ordinary-forward restored to protected-base spelling before merge.

Exact-head hosted checks must be read from GitHub after the final content head settles; predecessor receipts are not promoted to a later commit identity.

### RED → GREEN acceptance

1. **RED:** the focused regressions fail when `_reject_legacy_table_split()` returns to generated `IN (%s, ...)` query text, binds any candidate value into SQL text, changes the one-list parameter envelope, or drops any expected candidate.
2. **GREEN:** the minimum production delta uses structurally static `table_name = ANY(%s)` with one bound candidate array while preserving legacy rejection semantics.
3. Full repository tests and owned statement/branch coverage remain at repository-required thresholds on the same exact head.
4. Bandit/SAST/Security and CodeQL are evaluated on that exact head. Scanner or workflow failures are root-caused; warnings are not suppressed to manufacture GREEN.
5. Current-head independent review has no unresolved valid finding. Model/bot review is supporting evidence, not self-approval.
6. Merge occurs only through normal protected governance. Any central CI defect is handed to its canonical owner with immutable repo/PR/head/base/run evidence rather than worked around in this repository.

### Release effect

This is a database-query refactor unless new exploit evidence establishes a security defect. Release notes must not describe it as a MEDIUM SQL-injection fix merely because a static analyzer classified the previous query construction pattern.

## Traceability

- PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row and array comparisons*. https://www.postgresql.org/docs/18/functions-comparisons.html
- Psycopg Team. (2026). *Psycopg 3 documentation: Adapting basic Python types — Lists adaptation*. https://www.psycopg.org/psycopg3/docs/basic/adapt.html#lists-adaptation
- Psycopg Team. (2026). *Psycopg 3 documentation: Differences from psycopg2*. https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html
- Psycopg Team. (2026). *Psycopg 3 documentation: Cursor classes*. https://www.psycopg.org/psycopg3/docs/api/cursors.html
- Psycopg Team. (2026). *Psycopg 3 documentation: SQL string composition*. https://www.psycopg.org/psycopg3/docs/api/sql.html
- Repository evidence: `ContextualWisdomLab/mhtml-etl-gateway` PR #79, protected base `main@e3d21b0a44ab8430009160e4005df18351bf27c9`.

## System lineage namespace collision

### Problem boundary

MHTML sources supply arbitrary business headers which the ETL gateway normalizes into 63-character PostgreSQL identifiers. The ETL schema definition additionally claims four reserved identifiers for system lineage (`source_artifact_path`, `source_artifact_sha256`, `source_row_number`, and `loaded_at`). If a business header normalizes exactly to one of these reserved names, the `TableSchema.create_ddl(include_lineage=True)` contract attempts to declare the same column twice, yielding invalid DDL.

The repair requires reserving system identifiers during schema inference before business-name allocation.

### Domain and data invariants

- The four system identifiers (`source_artifact_path`, `source_artifact_sha256`, `source_row_number`, `loaded_at`) are unconditionally reserved.
- Business column names that collide with system identifiers must be deterministically suffixed (e.g., `_2`) while remaining <=63 characters.
- System lineage columns always retain authority and exact semantic meaning.
- Ordinary column-name allocations must remain deterministic and reproducible.

### Current evidence and gap

PR #87 owns the implementation. Hosted RED was confirmed at exact head `73eb21cf1f01f476f2ca64073c3e6ddf8fc3f407` where colliding business headers caused DDL failures.
The candidate repair sits at `68117c62ced82260027eaa116c3f8a39012fd1c0`, which pre-reserves system identifiers through the existing uniqueness allocator.

Acceptance remains blocked pending full CI/CD validation.

### RED → GREEN acceptance

1. **RED:** The system fails or generates invalid DDL when business headers normalize to `source_artifact_path`, `source_artifact_sha256`, `source_row_number`, or `loaded_at`.
2. **GREEN:** The system successfully processes such headers by deterministically suffixing them, yielding exactly one instance of each system identifier in the emitted DDL.
3. Candidate repair #87 must first obtain unchanged-head Repository Quality/coverage, Security/SAST, and canonical CodeQL acceptance before the gap is marked resolved.
4. After #87 is protected-integrated, baseline status must reference the immutable protected/release identity rather than the feature head.

### Traceability

- Repository evidence: `ContextualWisdomLab/mhtml-etl-gateway` PR #87.
