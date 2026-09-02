# Changelog

All notable changes follow Keep a Changelog, and versions follow Semantic Versioning.

## [Unreleased]

### Changed

- The hourly workflow's three OpenCode invocations route scheduled model
  traffic through the org's `contextual-orchestrator` gateway, pinned to the
  fail-closed `orchestrator/free` pool, instead of calling NVIDIA NIM
  directly. See ADR-0021 and `ContextualWisdomLab/mhtml-etl-gateway#60`.

### Planned

- Staging schemas, rejection quarantine, reconciliation, replay, tenant-aware
  APIs, and authenticated governed CWL connectors.

## [0.4.0] — 2026-08-12

### Added

- A first-party `propose` CLI and Python wrapper that turn one validated MHTML
  table into a deterministic, value-free schema proposal for steward review and
  Semantic Data Portal or pg-erd-cloud handoff.

## [0.3.2] — 2026-08-12

### Added

- A value-free pg-erd-cloud DBML visualization handoff plan for reviewed schema
  proposals, without network, authentication, or diagram persistence authority.

## [0.3.1] — 2026-08-12

### Added

- Stream typed live PostgreSQL rows through Psycopg `COPY FROM STDIN` while
  preserving the existing per-artifact catalog and lineage transaction.

### Changed

- Load results expose queryable counts and table identity without row samples;
  value queries remain an explicit caller-authorized database action.

## [0.3.0] — 2026-08-12

### Added

- Bounded, non-rendering MHTML inspection with RFC 2387 root selection,
  deterministic table extraction, resource budgets, and fixed error contracts.
- PostgreSQL ETL with validation, idempotent artifact cataloging, opaque lineage,
  schema inference, JSON/CSV/PPTX column mappings, and `COMMENT ON COLUMN` DDL.
- Value-free schema proposal and approval-boundary documentation, PRD/TRD,
  architecture/UML/ERD, threat model, operability, compliance mapping, test
  strategy, ADR index, and APA 7th research traceability.
- A deterministic, value-free Semantic Data Portal graph manifest connector for
  schema-proposal discovery, with caller-owned authentication and transport.
- An approval-, tenant-, and actor-bound Semantic Data Portal handoff envelope
  with deterministic per-request idempotency keys and no raw source values.
- A caller-owned governed catalog publisher that records value-free remote
  acceptance receipts only for explicit 2xx responses, with safe partial-outcome
  errors and no request or provider bodies.
- Python 3.11–3.14 quality matrix and privacy/security regression fixtures.

### Changed

- CLI now exposes inspection, single-load, and batch commands through one
  privacy-safe argument and output contract.
- Public reports, errors, batch summaries, and lineage never echo source paths,
  filenames, row values, or raw Content-Location values.
- Schema evolution promotes incompatible live PostgreSQL columns transactionally;
  mapping comments are applied with the table setup.
- Enforce multiword lowercase `snake_case` database names across inference,
  DDL, `COMMENT ON COLUMN`, and dynamic SQL; canonicalize single-token inputs
  with `_field`/`_table` suffixes and migrate the catalog status column to
  `load_status_code`.
- Fail closed when a persisted legacy table or column would otherwise coexist
  with a parallel suffixed object; operators receive an explicit migration
  requirement until the dynamic-object migration and rollback contract is
  implemented.
- Add an explicit catalog status-column down migration and reject ambiguous
  dual-column states in both migration directions.
- Bound signed BIGINT inference, reject arbitrary PostgreSQL DDL types, and
  normalize database/identifier failures without reflecting secrets or provider
  details.

### Security

- Active content, browser rendering, XML entity resolution, office execution,
  and external resource retrieval remain structurally excluded.
- Source, MIME, HTML, table, span, row, column, and cell budgets fail closed.
- OpenCode/Strix workflows preserve exact-head, secret-isolation, least-privilege,
  and central merge-governance boundaries.

## [0.2.1]

### Fixed

- Required-header validation, ZCRHT shape detection, span handling, batch
  rollback, type promotion, action pinning, and Docker health checks.

## [0.2.0]

### Added

- Fail-closed validation, ingest catalog, idempotent loading, batch discovery,
  memory-bounded parsing, and optional Docker execution.

## [0.1.0]

### Added

- Initial MHTML parser, HTML table extractor, schema inference, PostgreSQL
  loader, lineage model, CLI, and architecture contracts.
