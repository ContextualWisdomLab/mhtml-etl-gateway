# MHTML ETL Gateway Architecture v0.1

## Runtime Flow

```text
MHTML Artifact
    |
    v
Raw Import Layer (read-only; sha256 lineage)
    |
    v
MIME Parser
    |
    v
HTML Table Extractor
    |
    v
Schema Inference
    |
    v
Validation Engine (fail-closed)
    |
    v
PostgreSQL Loader
    |
    v
Governed Data Asset + lineage columns
```

## Trust Boundaries

- Raw artifacts are immutable.
- Embedded scripts are never executed.
- External resources are never fetched during parsing.
- Every loaded record has lineage metadata.

## Implemented Modules

| Module | Package path | Role |
|--------|--------------|------|
| mhtml_parser | `mhtml_etl_gateway.mhtml_parser` | MIME multipart → HTML bytes |
| html_table_extractor | `mhtml_etl_gateway.html_table_extractor` | HTML → headers + rows |
| schema_inference_engine | `mhtml_etl_gateway.schema_inference` | columns → PG types + snake_case |
| postgres_loader | `mhtml_etl_gateway.postgres_loader` | DDL + insert (live or injectable sink) |
| lineage_tracker | `mhtml_etl_gateway.lineage` | sha256 / path / row provenance |
| pipeline | `mhtml_etl_gateway.pipeline` | orchestrates stages |
| cli | `mhtml_etl_gateway.cli` | launchable entry point |

## Lineage columns (every loaded table)

- `source_artifact_path` TEXT
- `source_artifact_sha256` TEXT
- `source_row_number` BIGINT
- `loaded_at` TIMESTAMP

## Deployment Direction

Docker-first modular services with PostgreSQL persistence and future worker orchestration.
Local/dev: `pip install -e .` and `mhtml-etl-gateway <file.MHTML> --dsn postgresql:///dbname`.
