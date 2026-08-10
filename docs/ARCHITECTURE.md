# MHTML ETL Gateway Architecture v0.2

## Runtime Flow

```text
MHTML Artifact (CLI path or batch discovery)
    |
    v
Single-read Raw Import (sha256 lineage; immutable source)
    |
    v
MIME Parser (HTML part only; no scripts; no network)
    |
    v
HTML Table Extractor (chunked feed; top-level table)
    |
    v
Validation Engine (fail-closed; required headers)
    |
    v
Schema Inference (PostgreSQL types + snake_case names)
    |
    v
Ingest Catalog check (sha256 + table_name)
    |
    +-- already loaded + on_duplicate=skip --> skip insert
    |
    +-- on_duplicate=replace --> delete rows for sha --> insert
    |
    v
PostgreSQL Loader (business rows + lineage columns)
    |
    v
Catalog upsert + Governed Data Asset
```

## Trust Boundaries

- Raw artifacts are immutable (never written back).
- Embedded scripts are never executed.
- External resources are never fetched during parsing.
- Real operator paths are env/CLI only — not baked into the repository.
- Every loaded record has lineage metadata; every successful load updates the catalog.

## Modules

| Module | Package | Role |
|--------|---------|------|
| mhtml_parser | `mhtml_etl_gateway.mhtml_parser` | MIME → HTML bytes (single-read file helper) |
| html_table_extractor | `mhtml_etl_gateway.html_table_extractor` | HTML → headers + rows (chunked feed) |
| validation_engine | `mhtml_etl_gateway.validation_engine` | Fail-closed pre-load checks |
| schema_inference | `mhtml_etl_gateway.schema_inference` | PG types + snake_case |
| ingest_catalog | `mhtml_etl_gateway.ingest_catalog` | Catalog DDL + entry model |
| postgres_loader | `mhtml_etl_gateway.postgres_loader` | Idempotent load + sinks |
| batch | `mhtml_etl_gateway.batch` | Directory/glob multi-file |
| pipeline | `mhtml_etl_gateway.pipeline` | Orchestration |
| cli | `mhtml_etl_gateway.cli` | `load` / `batch` entry points |

## Lineage columns (business tables)

- `source_artifact_path` TEXT
- `source_artifact_sha256` TEXT
- `source_row_number` BIGINT
- `loaded_at` TIMESTAMP

## Catalog table

`mhtml_ingest_artifact` PK `(source_artifact_sha256, table_name)`.

## Memory strategy

1. File is read once into a single buffer (`read_mhtml_file`).
2. HTML part is selected from MIME parts without re-encoding the full archive.
3. HTMLParser is fed in ≤256 KiB chunks so intermediate parse state grows with content, not with redundant full-string copies of the same HTML.

## Deployment

- Local: `pip install -e .` + `MHTML_ETL_DSN`
- CI: GitHub Actions runs fixture pytest
- Docker: image with CLI entrypoint; mount data at runtime
