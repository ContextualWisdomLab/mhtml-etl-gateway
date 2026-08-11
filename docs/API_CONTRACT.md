# API Contract

## Current scope

Version `0.1.0` exposes a deterministic, synchronous, local inspection API. It performs no database write, schema inference, network request, browser rendering, office execution, or external-resource retrieval.

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

## CLI

```text
mhtml-etl-gateway inspect SOURCE_PATH [--pretty]
                          [--max-source-bytes INTEGER]
```

Successful inspection writes exactly one JSON object to stdout and returns status `0`. Expected argument, source, MIME, decoding, or table failures write exactly one fixed-message JSON object to stderr and return status `2`. Unexpected programming defects are not reclassified as argument errors.

The public CLI has no header-value disclosure flag. Header access requires a future authenticated source-custody and schema-governance workflow; it is not an inspection-report feature.

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
