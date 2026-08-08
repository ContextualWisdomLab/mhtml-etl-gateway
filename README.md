# MHTML ETL Gateway

MHTML ETL Gateway converts untrusted enterprise MHTML exports into governed PostgreSQL-ready data assets. The current `0.1.0` slice is the deterministic inspection boundary: it identifies the immutable source, resolves the authoritative HTML root, extracts top-level tables without rendering, and emits a privacy-preserving structural report that can feed later schema and load stages.

## Current capabilities

- bounded `multipart/related` and standalone `text/html` parsing;
- RFC 2387 `start` root selection, first-body default-root behavior, and root-type validation;
- fail-closed handling of MIME parser defects, duplicate critical headers, duplicate root-selection parameters, ambiguous `Content-ID` values, and malformed spans;
- an explicit `missing_related_type` compatibility diagnostic for enterprise exporters that omit the otherwise required RFC 2387 `type` parameter;
- strict charset decoding with BOM support;
- explicit diagnostics for nonstandard enterprise transfer encodings treated as identity bytes;
- top-level HTML table extraction without a browser, JavaScript engine, CSS renderer, network client, XML parser, or office runtime;
- deterministic `rowspan` and `colspan` expansion with document-wide resource budgets;
- suppression of script, style, noscript, template, and embedded-resource payloads;
- immutable SHA-256 source identity;
- nonreflecting Content-Location metadata: only URI scheme and SHA-256 are exposed;
- metadata-only JSON that excludes every cell-derived value by default, including header text;
- explicit local `--include-header-values` opt-in for protected schema-design workflows;
- Python 3.11–3.14 support;
- 100% production statement, branch, and public-docstring gates;
- a private hourly OpenCode loop that first maintains one exact-head PR through RCA and feasible repository-owned repair, then develops one bounded product gap only when the PR queue is empty;
- inherited organization-wide review, security, and merge governance from `ContextualWisdomLab/.github`.

## Install and inspect

```bash
python -m pip install .
python -m mhtml_etl_gateway inspect export.mhtml --pretty
```

The default report includes the source hash and size, root content type, a non-sensitive Content-Location scheme plus a hash, table dimensions, header-source metadata, counts, and diagnostics. `headers` is an empty array unless a trusted operator explicitly adds `--include-header-values`:

```bash
python -m mhtml_etl_gateway inspect export.mhtml \
  --include-header-values \
  --pretty
```

Header values can contain customer names, internal field labels, or other sensitive business metadata. Opt-in output must therefore remain inside the same protected processing boundary as the source file.

## Safety boundary

MHTML is untrusted input. This project never follows `Content-Location`, `cid:`, image, stylesheet, form, iframe, or script references. Errors use stable codes and generic messages rather than echoing source paths, identifiers, charsets, transfer encodings, media types, or row values.

Customer MHTML files must never be committed. Tests use synthetic fixtures; protected real-file verification records only cryptographic identity and aggregate dimensions.

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

The next bounded slices add versioned schema proposals, human or policy approval, immutable raw/staging/normalized PostgreSQL layers, transaction-safe `COPY FROM STDIN`, row-level reconciliation, tenant-aware controls, service APIs/workers, and connectors to CWL data products. See [ROADMAP.md](docs/ROADMAP.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
