# Changelog

All notable changes follow Keep a Changelog, and versions follow Semantic Versioning.

## [Unreleased]

### Added

- A deterministic, value-free Semantic Data Portal graph manifest connector for
  schema-proposal discovery, with caller-owned authentication and transport.
- An approval-, tenant-, and actor-bound Semantic Data Portal handoff envelope
  with tenant- and approval-scoped deterministic per-request idempotency keys,
  strict governance-context validation, and no raw source values.

### Changed

- Enforce multiword lowercase `snake_case` database names across inference,
  DDL, `COMMENT ON COLUMN`, and dynamic SQL; canonicalize single-token inputs
  with `_field`/`_table` suffixes and migrate the catalog status column to
  `load_status_code`.
- Fail closed when a persisted legacy table or column would otherwise coexist
  with a parallel suffixed object; operators receive an explicit migration
  requirement until the dynamic-object migration and rollback contract is
  implemented.

### Planned

- Approved schema decisions, streamed transactional loading, rejection
  quarantine, reconciliation, replay, tenant-aware APIs, and authenticated
  governed CWL connectors.

## [0.3.0] — 2026-08-11

### Added

- Bounded, non-rendering MHTML inspection with RFC 2387 root selection,
  deterministic table extraction, resource budgets, and fixed error contracts.
- PostgreSQL ETL with validation, idempotent artifact cataloging, opaque lineage,
  schema inference, JSON/CSV/PPTX column mappings, and `COMMENT ON COLUMN` DDL.
- Value-free schema proposal and approval-boundary documentation, PRD/TRD,
  architecture/UML/ERD, threat model, operability, compliance mapping, test
  strategy, ADR index, and APA 7th research traceability.
- Python 3.11–3.14 quality matrix and privacy/security regression fixtures.

### Changed

- CLI now exposes inspection, single-load, and batch commands through one
  privacy-safe argument and output contract.
- Public reports, errors, batch summaries, and lineage never echo source paths,
  filenames, row values, or raw Content-Location values.
- Schema evolution promotes incompatible live PostgreSQL columns transactionally;
  mapping comments are applied with the table setup.

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
