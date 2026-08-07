# ADR 0005: Metadata-only default output

**Status:** Accepted
**Date:** 2026-08-07

## Context

Data rows, header labels, and Content-Location values can contain PII, customer identifiers, internal field names, usernames, drive letters, directories, and network topology. A structural inspection result is routinely copied into CI logs, issues, or support artifacts, where source-equivalent access controls may not exist.

## Decision

The default public report contains source hash/size, root media type, Content-Location scheme plus SHA-256, dimensions, header coordinate/source/count, and fixed diagnostics. It contains no data rows and no header values. Header text requires explicit `include_header_values=True` or CLI `--include-header-values` and inherits the source artifact's protection requirements.

Public errors and diagnostics use fixed text and never reflect attacker-controlled paths, identifiers, encodings, media types, or values.

## Consequences

- Routine inspection evidence is useful without copying operational values.
- Equality correlation remains possible through hashes, so hash access and retention are controlled.
- Schema designers can still retrieve headers in a protected workflow.
- Row transport and extraction require a separate governed artifact rather than expansion of this report.
