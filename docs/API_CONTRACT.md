# API Contract

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
    include_header_values: bool = False,
) -> InspectionReport
```

The function is deterministic for identical bytes, limits, package version, and Python-compatible parser behavior. It performs no network or database operation.

### `inspect_mhtml_file`

Reads one local path once and delegates to the byte API. Source-read failures produce `source_read_failed` without echoing the path.

## CLI

```text
mhtml-etl-gateway inspect SOURCE_PATH [--pretty]
                          [--include-header-values]
                          [--max-source-bytes INTEGER]
```

Expected parser failures return status `2` and one JSON object on stderr.

## Default report schema

```json
{
  "source_hash_sha256": "64 lowercase hex characters",
  "source_size_bytes": 467343,
  "root_content_type": "text/html",
  "root_content_location_scheme": "file",
  "root_content_location_hash_sha256": "64 lowercase hex characters",
  "table_count": 1,
  "diagnostics": [
    {"code": "missing_related_type", "message": "fixed generic text"}
  ],
  "tables": [
    {
      "table_index": 0,
      "row_count": 14,
      "data_row_count": 13,
      "column_count": 40,
      "header_row_index": 0,
      "header_source": "positional",
      "header_value_count": 40,
      "header_values_included": false,
      "headers": [],
      "diagnostics": [
        {"code": "positional_header", "message": "fixed generic text"}
      ]
    }
  ]
}
```

Values shown are structural examples. No source row or header value appears in the default representation.

## Protected header opt-in

When `include_header_values=True` or `--include-header-values` is used, `headers` contains the selected header row and `header_values_included` is true when a header exists. This is not a public-log mode; the caller must apply source-equivalent authorization, encryption, retention, and export controls.

## Diagnostics

Current document diagnostics include:

- `missing_related_type`;
- `identity_transfer_encoding`.

Current table diagnostics include:

- `positional_header`.

Diagnostics are nonfatal and have fixed messages. Fatal failures use `MhtmlGatewayError` and stable `ErrorCode` values.

## Compatibility policy

New fields may be added in a backward-compatible minor release. Existing field meaning, diagnostic code, and error code changes require an ADR and versioned contract. Cell values will not be added to the inspection report; row transport belongs to a separate future extraction/load artifact.

## Future service API

A network service will be defined in OpenAPI 3.2.0 only after authentication, tenancy, idempotency, object-storage custody, asynchronous job, and export-authorization contracts are implemented. The current package exposes no unauthenticated upload endpoint.
