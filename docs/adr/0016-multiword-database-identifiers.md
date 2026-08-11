# ADR-0016: Enforce multiword database identifiers

- Status: Accepted
- Date: 2026-08-11
- Owners: MHTML ETL Gateway maintainers

## Context

The product contract already promises descriptive database objects, but the
legacy inference and SQL boundary accepted one-word identifiers such as
`value`, `empty`, and `status`. That creates inconsistent generated schemas,
weakens cross-service discoverability, and makes it easy for a direct
`TableSchema` caller to bypass the naming rule. PostgreSQL also truncates
unquoted identifiers at 63 bytes, so a suffix must be reserved before a
single-token name is shortened.

## Decision

1. Column inference converts a single-token header to a bounded name ending in
   `_field`; table inference converts a single-token table input to a bounded
   name ending in `_table`.
2. `require_safe_ident` accepts only lowercase ASCII `snake_case` identifiers
   with at least two components and a maximum of 63 UTF-8 bytes. It remains the
   fail-closed gate for every dynamic table and column identifier.
3. The fixed ingest catalog uses `load_status_code` instead of the one-word
   SQL column `status`.
4. Startup catalog setup runs a constant, reversible compatibility migration
   that renames an existing `status` column to `load_status_code` when the new
   column is absent. No caller value is interpolated into this migration.
5. Mapping inputs may continue to use a steward's one-word target spelling;
   the same canonicalization resolves it to the generated multiword column.
   Direct callers constructing an unsafe `TableSchema` receive the existing
   `UnsafeIdentifierError` before DDL or row writes.
6. The fixed-catalog rename does not authorize a guessed migration for dynamic
   business tables or columns. When the live sink detects a legacy one-word
   predecessor, it must fail closed before creating a parallel suffixed object
   and require an explicit migration with collision, rollback, and recovery
   evidence.

## Consequences

- New generated DDL and `COMMENT ON COLUMN` statements have a uniform,
  descriptive naming contract.
- Legacy single-token inferred column names change (for example, `MANDT` maps
  to `mandt_field`), so downstream consumers must use the returned schema and
  must not hard-code old names.
- Existing ingest catalogs upgrade in place through a deterministic column
  rename; the migration is safe to replay and does not change catalog values.
- Existing dynamic business objects do not yet migrate automatically. The
  fail-closed split guard prevents mixed old/new writes, while an explicit
  migration and rollback contract remains a known gap before this decision is
  integration-ready.
- The policy is deliberately narrower than PostgreSQL's full identifier
  grammar. It avoids quoted, case-sensitive, dollar-sign, and one-word names
  to keep generated SQL portable and reviewable.

## Verification

`tests/test_schema_inference.py`, `tests/test_column_mapping.py`,
`tests/test_postgres_loader.py`, and `tests/test_legacy_etl_quality.py` cover
single-token canonicalization, 63-byte suffix preservation, direct unsafe
identifier rejection, mapping compatibility, realistic `COMMENT ON COLUMN`
DDL, catalog-column migration SQL, and in-memory/live-sink write boundaries.
The persisted-upgrade regressions additionally prove that a legacy table or
column blocks parallel object creation and reports the explicit migration
requirement without interpolating the legacy identifier into SQL.

## References

- PostgreSQL Global Development Group. (2026). *4.1. Lexical structure*.
  PostgreSQL 18 documentation.
  https://www.postgresql.org/docs/current/sql-syntax-lexical.html
