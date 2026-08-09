# ADR 0005: Value-free public inspection output

**Status:** Accepted  
**Date:** 2026-08-09

## Context

MHTML data rows, header labels, media metadata, and Content-Location values can contain PII, customer identifiers, internal field names, usernames, paths, network topology, and attacker-selected text. Structural inspection results are routinely copied into CI logs, issues, or support artifacts where source-equivalent access controls may not exist.

A boolean command-line opt-in is not an authorization or source-custody mechanism. Exposing headers through stdout would make protected values easy to redirect into an unsafe artifact and would contradict the public inspection report's nonreflection boundary.

## Decision

The public `InspectionReport` contains only:

- exact source SHA-256 and byte size;
- SHA-256 of Content-Location when present, without raw value or scheme;
- table count and array order;
- table row, data-row, and column counts;
- header row coordinate, semantic/positional classification, and header value count;
- fixed nonreflecting diagnostics.

It excludes data rows, header values, decoded HTML, raw Content-ID and Content-Location, Content-Location scheme, source-controlled media type, charset, transfer encoding, paths, and embedded payloads.

The public Python API and CLI provide no header-value disclosure option. Header access required by future schema governance must use a separate authenticated source-custody workflow with explicit authorization, encrypted or protected output, retention policy, export controls, and immutable audit evidence.

Public errors and diagnostics use approved fixed text and never reflect caller-provided or source-controlled detail.

## Consequences

- Routine inspection evidence can be attached to operational records without copying customer values.
- The source and location hashes still permit equality correlation, so access and retention controls apply to them.
- Schema proposal development cannot rely on public stdout; it must implement the protected workflow first.
- Row transport and schema evidence remain separate governed artifacts rather than expansions of the inspection report.
- Removing source-controlled classifications reduces diagnostic detail but preserves the stronger public confidentiality boundary.
