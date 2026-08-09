# MHTML ETL Gateway

MHTML ETL Gateway currently provides deterministic, privacy-preserving inspection of untrusted enterprise MHTML exports. Version `0.1.0` identifies the immutable source, resolves the authoritative HTML root, extracts bounded top-level table structure without rendering, and emits a value-free structural report. Governed PostgreSQL schema proposals and loading are the next product milestones, not current package capabilities.

## Current capabilities

- bounded `multipart/related` and standalone `text/html` parsing;
- RFC 2387 `start` selection and first-direct-body default-root behavior;
- fail-closed MIME defects, duplicate critical headers and parameters, ambiguous `Content-ID` values, contradictory root types, invalid charsets, malformed spans, and exhausted budgets;
- total MIME entity and nesting-depth budgets, including stable conversion of parser recursion exhaustion to `mime_nesting_too_deep`;
- strict charset decoding with BOM support and explicit diagnostics for known enterprise compatibility deviations;
- top-level HTML table extraction without a browser, JavaScript engine, CSS renderer, network client, XML parser, office runtime, or external resource retrieval;
- deterministic `rowspan` and `colspan` expansion with duplicate-attribute, overlap, raw-cell, projected-cell, row, and column budgets;
- exact nested suppression of `script`, `style`, `noscript`, `template`, `iframe`, and `object`, while void `embed` resources are ignored without swallowing following text;
- immutable SHA-256 source identity;
- raw Content-Location replacement with SHA-256 only;
- metadata-only JSON that excludes every cell-derived value, including header text;
- fixed nonreflecting public error messages;
- Python 3.11–3.14 support;
- 100% production statement, branch, and public-docstring gates;
- an hourly private OpenCode loop that drains executable PR work, shared blockers, and proven-disjoint buyer-visible work rather than stopping after one patch or external delay;
- repository-controlled tests and builds executed through a secret-stripped unprivileged wrapper;
- inherited organization-wide review, security, branch-freshness, and merge governance from `ContextualWisdomLab/.github`.

## Install and inspect

```bash
python -m pip install .
python -m mhtml_etl_gateway inspect export.mhtml --pretty
```

The report contains source identity and size, hashed Content-Location identity when present, table dimensions, header coordinate/source/count metadata, and fixed diagnostics. It contains no header or row values.

```json
{
  "source_hash_sha256": "…",
  "source_size_bytes": 467343,
  "root_content_location_hash_sha256": "…",
  "table_count": 1,
  "diagnostics": [],
  "tables": [
    {
      "row_count": 14,
      "data_row_count": 13,
      "column_count": 40,
      "header_row_index": 0,
      "header_source": "positional",
      "header_value_count": 40,
      "diagnostics": []
    }
  ]
}
```

Header access for schema design requires a future authenticated source-custody workflow with authorization, audit, retention, and protected output. The public inspection API and CLI do not expose a header-value option.

Programmatic callers can lower all parser budgets through `ParseLimits`, including source bytes, total MIME entities, MIME depth, decoded HTML characters, tables, rows, columns, raw and normalized cells, and cell text. Every budget must be a positive non-boolean integer.

## Safety boundary

MHTML is untrusted input. The project never follows `Content-Location`, `cid:`, image, stylesheet, form, iframe, object, embed, or script references. Errors use stable codes and fixed messages rather than echoing paths, identifiers, charsets, transfer encodings, media types, boundary values, headers, or rows.

Customer MHTML files must never be committed. Tests use synthetic fixtures. Protected real-file validation records only authorized aggregate evidence and never publishes the source path, values, or actual source hash.

The scheduled coding agent treats repository source, comments, issues, reviews, logs, and artifacts as untrusted data. Repository-controlled code runs through `cwl-safe-exec`, which removes model, GitHub, OIDC, and provider credentials and executes under the dedicated unprivileged `cwl-untrusted` identity with workspace-only group access.

## Development verification

```bash
PYTHONPATH=src coverage erase
PYTHONPATH=src coverage run --branch -m unittest discover -s tests -t . -v
PYTHONPATH=src coverage report --show-missing --fail-under=100
python -m compileall -q src tests scripts
PYTHONPATH=src python scripts/validate_repository.py
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
```

Start with the [PRD](docs/PRD.md), [TRD](docs/TRD.md), [architecture](docs/ARCHITECTURE.md), [API contract](docs/API_CONTRACT.md), and [security contract](docs/SECURITY.md).

## Product path

The next bounded slices are:

1. versioned protected schema proposals and approval;
2. immutable raw/staging/normalized PostgreSQL layers;
3. transaction-safe streamed `COPY FROM STDIN`;
4. row-level lineage, rejection quarantine, reconciliation, rollback, and idempotent replay;
5. tenant-aware service APIs, workers, observability, and lifecycle controls;
6. governed connectors to CWL data products.

See [ROADMAP.md](docs/ROADMAP.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
