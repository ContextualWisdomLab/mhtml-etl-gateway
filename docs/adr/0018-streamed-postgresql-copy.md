# ADR-0018: Stream PostgreSQL rows with `COPY FROM STDIN`

**Status:** Accepted

**Date:** 2026-08-12

## Context

The live `PsycopgSink` previously materialized every typed row and sent the
batch through `executemany()`. That is correct for small fixtures, but it adds
per-row statement overhead and does not use PostgreSQL's bulk data path. The
loader already owns one explicit transaction, validates identifiers, and keeps
source-row lineage in the target relation.

## Decision

Use Psycopg 3's row-adapting `Cursor.copy()` API with a dynamically composed,
identifier-allowlisted `COPY <table> (<columns>) FROM STDIN` statement. Send
each typed row with `write_row()` inside the copy context, then upsert the
artifact catalog and commit the same transaction.

The gateway does not use server-side filenames or `PROGRAM`; source bytes stay
under caller custody and the database receives data through the authenticated
client connection. Any copy, catalog, or commit failure rolls back the whole
load and exposes only the fixed `database load failed` error. The existing
in-memory sink remains the deterministic test double.

This decision delivers the bulk transport slice only. Rejection quarantine,
accepted/rejected reconciliation, staging schemas, tenant RLS, and asynchronous
job controls remain separate milestones and must not be inferred from this
implementation.

## Consequences

- Large valid loads use PostgreSQL's streaming copy protocol and preserve
  transaction atomicity.
- Dynamic identifiers remain restricted to validated schema names; row values
  continue through Psycopg adaptation rather than SQL interpolation.
- Tests must verify the `COPY` statement, lineage columns, row adaptation, and
  rollback behavior with a fake copy context; a PostgreSQL integration test
  remains required for release evidence.
- Existing callers and the public CLI do not change.

## References

- PostgreSQL Global Development Group. (2026). *COPY*. PostgreSQL 18.4
  documentation. https://www.postgresql.org/docs/18/sql-copy.html
- Psycopg Authors. (n.d.). *Using COPY TO and COPY FROM*. Psycopg 3
  documentation. Retrieved August 12, 2026, from
  https://www.psycopg.org/psycopg3/docs/basic/copy.html
