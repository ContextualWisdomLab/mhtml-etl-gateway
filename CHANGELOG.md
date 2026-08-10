# Changelog

## [Unreleased]

### Added

- MHTML MIME parser (`mhtml_parser`) for multipart Excel Web Archive / SAP ALV exports.
- Top-level HTML table extractor that keeps nested cell markup as cell text.
- Schema inference engine mapping columns to PostgreSQL types with multiword snake_case names.
- PostgreSQL loader with lineage columns (`source_artifact_path`, `source_artifact_sha256`, `source_row_number`, `loaded_at`).
- CLI entry point `mhtml-etl-gateway` (DSN via `--dsn` / `MHTML_ETL_DSN` / `DATABASE_URL`; `--dry-run` offline path).
- Pytest suite with SAP ALV–shaped fixture (`tests/fixtures/zcrht811_sample.MHTML`).
- Initial MHTML ETL Gateway repository baseline.
- Architecture and agent development contracts.

### Security

- Established immutable raw artifact and active-content isolation policies.
- Parser never executes embedded scripts and never fetches external resources; parse failures fail closed.
