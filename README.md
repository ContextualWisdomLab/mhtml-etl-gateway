# MHTML ETL Gateway

Enterprise MHTML ingestion gateway that converts browser, SAP ALV, and Excel Web Archive exports into governed PostgreSQL data assets.

## Product Principles

- Immutable raw artifact preservation
- Deterministic MIME/HTML parsing
- Schema inference with validation gates
- PostgreSQL governed loading
- Full lineage and audit evidence
- No active HTML execution

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Current Status

Documentation baseline established. Implementation follows PRD/TRD/ADR driven development.
