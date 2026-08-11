# Changelog

## [Unreleased]

### Added

- Column mapping references from JSON, CSV, or PPTX text layers.
- Safe `COMMENT ON COLUMN` generation and live PostgreSQL application, with
  matched/unmatched mapping evidence in pipeline results.
- Privacy boundary for runtime ingestion: opaque artifact references and a
  filename-independent default table name in pipeline/batch reports and lineage.

## [0.2.1] — Unresolved

### Fixed

- Validation: case-insensitive required headers; ZCRHT shape detection without circular MANDT/GUID dependency.
- HTML extractor: honor `colspan`; replace `assert` with fail-closed errors.
- Schema: collision-safe unique snake_case (including `A`/`A_2`/`A`); shared int/decimal parse helpers.
- Batch: rollback shared Postgres sink on per-file failure; safer absolute globs.
- Loader: type promote + insert in one transaction; public `rollback()` for batch recovery.
- CI/Dockerfile: pin actions and base image digests; non-root already required.
- Dockerfile: add HEALTHCHECK for CLI entrypoint (Strix medium finding).

## [0.2.0] — Unresolved

### Added

- Fail-closed **validation engine** (required headers incl. `MANDT`/`GUID` for ZCRHT811-shaped tables; row shape; non-empty data).
- **Ingest catalog** table `mhtml_ingest_artifact` and loader integration.
- **Idempotent load** via `--on-duplicate skip|replace` keyed by content sha256 + table name.
- **Batch** CLI (`mhtml-etl-gateway batch`) with directory/glob discovery and summary report; `MHTML_ETL_SOURCE_DIR` env.
- Memory-bounded file read + chunked HTML parser feed.
- GitHub Actions CI (fixture pytest) and optional Dockerfile.
- Tests: validation, idempotency, batch multi-file, memory path.

### Changed

- CLI uses `load` / `batch` subcommands (bare path still works as `load`).
- Package version 0.2.0.

### Security

- Real CRM absolute paths must not be committed; operator paths via env/CLI only.
- Parser never executes scripts or fetches remote resources.

## [Unreleased] / 0.1.0 baseline

### Added

- Initial MHTML MIME parser, HTML table extractor, schema inference, PostgreSQL loader, lineage, CLI.
- Architecture and agent development contracts.
