# MHTML ETL Gateway Architecture v0.1

## Runtime Flow

```text
MHTML Artifact
    |
    v
Raw Import Layer
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
Validation Engine
    |
    v
PostgreSQL Loader
    |
    v
Governed Data Asset
```

## Trust Boundaries

- Raw artifacts are immutable.
- Embedded scripts are never executed.
- External resources are never fetched during parsing.
- Every loaded record has lineage metadata.

## Planned Modules

- mhtml_parser
- html_table_extractor
- schema_inference_engine
- validation_engine
- postgres_loader
- lineage_tracker

## Deployment Direction

Docker-first modular services with PostgreSQL persistence and future worker orchestration.
