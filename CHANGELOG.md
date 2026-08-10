# Changelog

## [0.2.0] — Unreleased

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
