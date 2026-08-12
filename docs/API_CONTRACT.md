# API Contract

## Current scope

Version `0.3.2` exposes deterministic, synchronous, local inspection, schema
proposal, mapping, value-free catalog-manifest, and governed handoff APIs. It
performs no database write through the catalog connector, network request,
browser rendering, office execution, or external-resource retrieval.

## Python API

```python
from mhtml_etl_gateway import ParseLimits, inspect_mhtml_bytes, inspect_mhtml_file
```

### `inspect_mhtml_bytes`

```python
inspect_mhtml_bytes(
    source_bytes: bytes,
    *,
    limits: ParseLimits | None = None,
) -> InspectionReport
```

The function is deterministic for identical bytes, limits, package version, and supported Python parser behavior. It returns structural metadata only. No cell-derived value, including header text, is present in the report.

### `ParseLimits`

```python
ParseLimits(
    max_source_bytes=250 * 1024 * 1024,
    max_mime_parts=256,
    max_mime_depth=64,
    max_html_chars=50_000_000,
    max_tables=128,
    max_rows_per_table=1_000_000,
    max_columns_per_table=4096,
    max_total_cells=10_000_000,
    max_cell_text_chars=1_000_000,
)
```

`max_mime_parts` counts every descendant MIME body entity, including multipart containers. `max_mime_depth` counts direct body parts at depth 1. `max_total_cells` bounds both raw source-cell construction and normalized logical cells. Every value must be a positive non-boolean integer.

### `inspect_mhtml_file`

```python
inspect_mhtml_file(
    source_path: str | pathlib.Path,
    *,
    limits: ParseLimits | None = None,
) -> InspectionReport
```

The file wrapper reads one local path and delegates to the byte API. Source-read failures produce `source_read_failed` without reflecting the path.

### `propose_schema_from_mhtml`

```python
propose_schema_from_mhtml(
    source_path: str | pathlib.Path,
    *,
    data: bytes | None = None,
    policy: SchemaProposalPolicy | None = None,
    limits: ParseLimits | None = None,
) -> SchemaProposal
```

This local source-custody wrapper extracts one validated table and converts its
protected headers and rows into the existing deterministic, value-free
`SchemaProposal`. Complete extracted columns are marked `complete=True` for
nullability evidence. The returned proposal contains only fingerprints,
normalized names, allow-listed types, aggregate counts, and review reasons.
It performs no database, network, authentication, LLM, or file-write operation.
Callers remain responsible for source authorization, access, retention, and
approval before sharing the proposal with a connector.

### `build_semantic_catalog_manifest`

```python
build_semantic_catalog_manifest(
    proposal: SchemaProposal,
    *,
    catalog_name: str,
) -> SemanticCatalogManifest
```

This in-process connector converts a value-free schema proposal into a
deterministic manifest whose `nodes` and `edges` match the current
Semantic Data Portal `GraphNodeRequest` and `GraphEdgeRequest` shapes. It does
not submit the requests. The caller owns authentication, actor identity,
tenant policy, approval, retries, and HTTP transport.

The manifest contains proposal fingerprints, normalized target names, aggregate
evidence, review reasons, and `privacy_mode: "value_free"`. It never contains
raw source headers or sample values and performs no network, database, LLM, or
file operation. See [the connector contract](SEMANTIC_CATALOG_CONNECTOR.md).

### `build_semantic_catalog_submission_envelope`

```python
build_semantic_catalog_submission_envelope(
    manifest: SemanticCatalogManifest,
    *,
    tenant_id: str,
    actor: str,
    approval_reference: str,
) -> CatalogSubmissionEnvelope
```

This function binds a value-free manifest to an opaque tenant reference, an
explicit actor, and an approval reference. It produces an envelope containing
`envelope_id`, `contract_version`, `target_system`, `manifest_id`, the claimed
governance context, and ordered `POST` request plans for `/graph/nodes` and
`/graph/edges`. Each request has a deterministic `idempotency_key` scoped by
tenant and approval reference plus an actor-bearing request body. The envelope
ID changes when governance context changes. The function does not authenticate,
authorize, send, retry, persist, or mutate the manifest; the caller-owned
publisher must provide actor authentication, tenant authorization, approval
verification, credentials, TLS, remote acceptance, and immutable audit.

### `publish_catalog_submission`

```python
publish_catalog_submission(
    envelope: CatalogSubmissionEnvelope,
    transport: CatalogTransport,
    evidence: CatalogPublisherEvidence,
    *,
    max_requests: int = 4096,
) -> CatalogPublicationReceipt
```

This transport-neutral boundary publishes a previously validated envelope
through a caller-owned adapter. The caller must prove actor authentication,
tenant authorization, approval verification, and provide an opaque immutable
audit reference. Each request must receive an explicit accepted `2xx` response
and an opaque remote request ID before a value-free publication receipt is
returned. The publisher sends each request once and owns no credentials,
network, TLS, retry, persistence, or policy authority.

The receipt contains the envelope ID, target, audit reference, accepted count,
and safe request/remote IDs. It excludes request bodies, source headers, sample
values, credentials, and provider error bodies. A provider exception, rejection,
invalid response, or partial accepted prefix raises `CatalogPublisherError` with
only a stable code, failing request index, and accepted prefix count. The
transport may implement RFC 9110 status handling, RFC 9457 problem details, and
W3C Trace Context independently at the application boundary.

## CLI

```text
mhtml-etl-gateway inspect SOURCE_PATH [--pretty]
                          [--max-source-bytes INTEGER]
mhtml-etl-gateway propose SOURCE_PATH [--pretty]
                          [--max-source-bytes INTEGER]
```

Successful inspection writes exactly one JSON object to stdout and returns status `0`. Expected argument, source, MIME, decoding, or table failures write exactly one fixed-message JSON object to stderr and return status `2`. Unexpected programming defects are not reclassified as argument errors.

`propose` writes one RFC 8259-compatible JSON object containing the value-free
schema proposal and returns status `0`. Its source/header values are read only
inside the local protected workflow; malformed sources use the fixed parser or
`schema_proposal_failed` error. The inspection CLI still has no header-value
disclosure flag, and neither command emits raw headers or cells.

## Public report schema

```json
{
  "source_hash_sha256": "64 lowercase hex characters",
  "source_size_bytes": 467343,
  "root_content_location_hash_sha256": "64 lowercase hex characters or null",
  "table_count": 1,
  "diagnostics": [
    {
      "code": "missing_related_type",
      "message": "fixed approved-safe text"
    }
  ],
  "tables": [
    {
      "row_count": 14,
      "data_row_count": 13,
      "column_count": 40,
      "header_row_index": 0,
      "header_source": "positional",
      "header_value_count": 40,
      "diagnostics": [
        {
          "code": "positional_header",
          "message": "fixed approved-safe text"
        }
      ]
    }
  ]
}
```

The array order preserves document table order. No sequential table identifier is exposed. `header_row_index` is a coordinate within one table rather than a persistent external identifier.

The report deliberately excludes:

- data-row and header values;
- decoded HTML;
- raw Content-ID and Content-Location;
- Content-Location scheme;
- source-controlled media type, charset, and transfer encoding;
- resource payloads and active-content text;
- local source path.

The source SHA-256 is part of the lineage contract. Access and retention policy still apply because hashes permit equality correlation.

## Diagnostics

Current nonfatal document diagnostics include:

- `missing_related_type`;
- `identity_transfer_encoding`.

Current table diagnostics include:

- `positional_header`.

Diagnostic messages are fixed and nonreflecting.

## Fatal error contract

Fatal failures use `MhtmlGatewayError` and stable `ErrorCode` values. Public serialization contains only:

```json
{
  "error_code": "stable_machine_code",
  "message": "fixed approved-safe text"
}
```

Current codes cover invalid arguments, source read/size failures, invalid or ambiguous MIME, MIME entity/depth limits, missing roots, charset/decoding failures, decoded HTML limits, table/row/column/cell/text limits, nested tables, and invalid spans.

`mime_nesting_too_deep` covers both an explicit `max_mime_depth` violation after parsing and standard-library recursion exhaustion during MIME parsing. Raw Python recursion exceptions do not escape the public parser contract.

## Compatibility policy

Backward-compatible fields may be added in a minor release only when they preserve the value-free and nonreflection boundary. Removing fields, changing field meaning, changing error/diagnostic semantics, or adding protected values requires a versioned contract and ADR.

Cell values will not be added to `InspectionReport`. Future extraction and load artifacts will be separate authorized contracts with source custody, lineage, approval, and retention controls.

## Future service API

A network service will be defined in OpenAPI only after authentication, tenancy, idempotency, encrypted object-storage custody, asynchronous jobs, cancellation/retry, export authorization, and audit contracts are implemented and verified. The current package exposes no upload endpoint.
