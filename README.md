# MHTML ETL Gateway

MHTML ETL Gateway is a deterministic, privacy-preserving ingestion boundary for
enterprise MHTML exports. It can inspect untrusted MIME/HTML structure without
rendering active content, infer governed PostgreSQL schemas, apply column mapping
references as `COMMENT ON COLUMN`, and load rows with opaque artifact lineage.

## Capabilities

- RFC 2387 `multipart/related` root resolution and standalone HTML support.
- Non-rendering, chunked table extraction with fail-closed MIME, HTML, span,
  row, column, cell, nesting, and source-size budgets.
- Validation of headers, row shapes, required business fields, and empty inputs.
- PostgreSQL type inference with multiword `snake_case` identifiers, idempotent
  artifact cataloging, transactional type promotion, streamed `COPY FROM STDIN`,
  and row-level lineage.
- JSON, CSV, and PPTX text-layer column mapping references for `COMMENT ON COLUMN`.
- Value-free, deterministic schema proposals, including a first-party `propose`
  CLI command, and a Semantic Data Portal graph manifest connector for
  dataset/column discovery without network side effects.
- Explicit actor, tenant, approval, and per-request idempotency context for a
  caller-owned Semantic Data Portal submission handoff.
- A value-free pg-erd-cloud DBML visualization handoff plan for opening reviewed
  schema proposals in a database diagram without network side effects.
- Privacy-safe reports and errors that do not echo local paths, filenames, row
  values, or raw Content-Location values.

## Install

```bash
python -m pip install -e ".[dev]"
```

Python 3.11–3.14 are supported. Live loads require PostgreSQL and either
`MHTML_ETL_DSN` or `DATABASE_URL`; dry runs do not require a database.

## Inspect an artifact

```bash
mhtml-etl-gateway inspect export.mhtml --pretty
```

Inspection output is metadata-only: source identity, size, table dimensions,
fixed diagnostics, and non-reflecting error codes. Cell and header values are
not emitted by the public inspection API.

## Propose a schema

```bash
mhtml-etl-gateway propose export.mhtml --pretty > schema-proposal.json
```

The proposal command is a local source-custody workflow. It reads the complete
table in protected process memory and emits a deterministic JSON proposal with
source/header fingerprints, normalized target names, conservative types,
aggregate evidence, and review reasons. It never emits raw headers, cell values,
decoded HTML, paths, or DDL. The proposal can be passed to the Semantic Data
Portal and pg-erd-cloud connector APIs after the caller's own approval and
authorization checks.

## Load one artifact

```bash
export MHTML_ETL_DSN="postgresql://user:pass@localhost:5432/dbname"
mhtml-etl-gateway load export.MHTML \
  --table-name zcrht811_export_rows \
  --on-duplicate skip \
  --json
```

Use `--dry-run` for parse, validation, type inference, and DDL generation without
writing to PostgreSQL. `--on-duplicate replace` replaces rows for an already
cataloged artifact; the default `skip` is idempotent.

## Column mappings and comments

Pass a JSON, CSV, or PPTX reference with `--column-mapping` (also accepted as
`--column-comments`):

```bash
mhtml-etl-gateway load export.MHTML \
  --column-mapping column-mapping.json \
  --ddl-out schema.sql \
  --dry-run
```

JSON records may use `source`, optional `target`, and `comment` (or
`description`/`label`):

```json
{
  "columns": [
    {"source": "ZCRHT811.TITLE", "target": "title", "comment": "상담 제목"},
    {"source": "ZCRHT810.ERDAT", "comment": "VOC 작성일자"}
  ]
}
```

Qualified source names match an extracted header by exact name or field suffix.
Ambiguous or conflicting mappings fail closed. PPTX support reads text-layer
tokens and slide sections; text embedded only in screenshots requires a JSON or
CSV mapping instead of implicit OCR.

## Semantic catalog handoff

```python
from mhtml_etl_gateway import (
    build_semantic_catalog_manifest,
    build_semantic_catalog_submission_envelope,
)

manifest = build_semantic_catalog_manifest(
    schema_proposal,
    catalog_name="SAP VOC export",
)
envelope = build_semantic_catalog_submission_envelope(
    manifest,
    tenant_id="tenant_cwl_production",
    actor="svc_catalog_publisher",
    approval_reference="approval_2026_08_11_001",
)
```

The manifest contains value-free dataset/column graph requests compatible with
`semantic-data-portal` `/graph/nodes` and `/graph/edges`. It is deterministic and
caller-owned. The envelope makes the actor, tenant, approval reference, and
stable per-request idempotency keys explicit while authentication, retry policy,
and network submission remain outside the gateway. See the
[connector contract](docs/SEMANTIC_CATALOG_CONNECTOR.md).

For a design-first database diagram, build a pg-erd-cloud request plan from the
same proposal:

```python
from mhtml_etl_gateway import build_pg_erd_visualization_plan

plan = build_pg_erd_visualization_plan(
    schema_proposal,
    catalog_name="SAP VOC export",
)
```

The plan targets `/api/dbml/convert`, contains no raw values or DBML records,
and leaves transport/authentication to the caller. See the
[pg-erd-cloud connector contract](docs/PG_ERD_CONNECTOR.md).

## Batch loading

```bash
export MHTML_ETL_SOURCE_DIR="/operator/local/source-directory"
mhtml-etl-gateway batch \
  --table-name mhtml_extracted_rows \
  --on-duplicate skip \
  --json
```

The batch output contains aggregate counts and opaque artifact references only.
The input directory is an operator-local runtime value and must never be
committed or embedded in documentation, tests, logs, or database lineage.

## Database contract

Every generated table and column uses at least two-word lowercase `snake_case`.
Single-token column headers receive a `_field` suffix and single-token table
inputs receive a `_table` suffix before PostgreSQL's 63-byte limit is applied.
Direct unsafe identifiers fail closed at the SQL boundary. Lineage columns are:

- `source_artifact_path TEXT`: `artifact:<sha-prefix>`, never a filesystem path;
- `source_artifact_sha256 TEXT`;
- `source_row_number BIGINT`;
- `loaded_at TIMESTAMP`.

The `mhtml_ingest_artifact` catalog is keyed by
`(source_artifact_sha256, table_name)` and uses `load_status_code` for its
status column. An upgrade-safe constant migration renames the legacy `status`
column when needed. Mapping comments are applied in the same setup transaction
as the table DDL and are never inferred from raw cell values.

## Verification

```bash
python -m pytest -q
python -m compileall -q src tests scripts
PYTHONPATH=src python scripts/validate_repository.py
```

The repository quality workflow exercises Python 3.11–3.14, exact pull-request
heads, dependency/security checks, static analysis, coverage, and package build
contracts. The quality gate is evidence for this repository; it is not a claim
of certification.

## Documentation and standards

Start with [PRD](docs/PRD.md), [TRD](docs/TRD.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [UML](docs/UML.md),
[DATA_MODEL](docs/DATA_MODEL.md), and [ERD](docs/ERD.md). Operational and
assurance material is in [OPERABILITY](docs/OPERABILITY.md),
[THREAT_MODEL](docs/THREAT_MODEL.md), [TEST_STRATEGY](docs/TEST_STRATEGY.md),
[COMPLIANCE_CONTROL_MAP](docs/COMPLIANCE_CONTROL_MAP.md), and
[VALIDATION_REPORT](docs/VALIDATION_REPORT.md). Decisions are indexed in
[docs/adr](docs/adr/README.md), and standards/papers are recorded in
[docs/doctoring/REFERENCES.md](docs/doctoring/REFERENCES.md) using APA 7th style.

The design considers NIST SSDF, OWASP ASVS, ISO/IEC 27001, CSAP readiness, SOC 2
Trust Services Criteria, RFC 2387/RFC 2557, OpenAPI, OpenTelemetry, SPDX, and
SLSA. The project does not claim those certifications.

## Modular deployment

The parser/inspection boundary is usable as a standalone library or service.
Future MSA boundaries separate source custody, deterministic parsing, schema
governance, PostgreSQL loading, audit/observability, and CWL connectors. The
semantic catalog connector is the first concrete ecosystem seam; it may consume
an approved value-free proposal but cannot bypass source validation,
authorization, or lineage controls. Candidate integrations include the central
`.github` workflows, `naruon`, `contextual-orchestrator`, `pg-erd-cloud`, and
governed PostgreSQL/lineage products.

## Safety

MHTML is untrusted input. The project never executes scripts, renders browsers,
resolves XML entities, fetches external resources, or follows active references.
Customer artifacts and real operator paths must never enter the repository.

## License

Apache License 2.0. See [LICENSE](LICENSE).
