# Test Strategy

## Principles

Every behavior change follows RED-GREEN-REFACTOR. Tests assert externally meaningful behavior and fail closed on ambiguity. Production statement, branch, and public-docstring coverage are exact 100% gates, not approximate targets.

## Current suites

### MIME

- standalone and multipart roots;
- explicit start, missing start target, non-HTML target, and cross-media duplicate IDs;
- ambiguity classification independent of MIME part ordering;
- first-direct-body default-root enforcement and nested-root rejection;
- missing, matching, and contradictory related type;
- parser defects, duplicate singleton headers, duplicate critical parameters;
- quoted semicolons, escaped quotes, nested comments, and malformed parameter fields;
- strict charset/BOM/UTF-8 paths;
- nonstandard transfer-encoding diagnostic;
- source, total MIME entity, and MIME depth limits;
- extreme nested multipart input that would otherwise raise `RecursionError`;
- stable `mime_nesting_too_deep` conversion;
- generic nonreflecting error text.

The extreme nesting regression uses 2,000 nested multipart entities with one HTML leaf. It must produce `MhtmlGatewayError` with `mime_nesting_too_deep`, never an unstructured Python recursion exception. A separate low-depth fixture verifies the configurable `max_mime_depth` boundary.

### HTML tables

- semantic and positional headers;
- Korean and rich text;
- block and line-break normalization;
- exact script/style/noscript/template suppression nesting;
- mismatched closing-tag resistance;
- nested-table rejection;
- irregular rows;
- rowspan/colspan expansion, gaps, overlap, and trailing implicit rows;
- table, row, column, cell, and text limits.

### Inspection and CLI

- default empty header values;
- explicit header opt-in;
- source SHA/size;
- Content-Location scheme/hash without raw location;
- stable JSON errors and exit codes;
- module and console entry points.

### Repository/workflows

- complete required documentation;
- full public docstrings;
- full-SHA Action pins;
- no committed MHTML;
- no prohibited Copilot token;
- NIM secret binding;
- OpenCode `share: false`;
- exact-head agent-branch quality execution;
- SHA-keyed push/PR concurrency;
- hash-locked binary-only quality dependency installation;
- dependency-integrity tests executed by `unittest discover`;
- PR-maintenance RCA and feasibility contract;
- fork read-only and stale-head lease rules;
- single-flight issue lease and no local merge-scheduler duplication.

## Realistic test policy

Synthetic fixtures model SAP-style codes with leading zeroes, compact dates, Korean text, rich cell content, nonstandard transfer encoding, and positional headers. A protected real export can be used in local/operator validation but is never committed and no value is printed. Its regression evidence is limited to exact source hash, byte size, aggregate table dimensions, diagnostic codes, and absence of raw protected metadata.

## Future loader tests

A PostgreSQL test container shall verify:

- migration up/down behavior;
- multiword naming contract;
- tenant RLS;
- streamed COPY;
- source/accepted/rejected/target count reconciliation;
- conversion-error quarantine;
- transaction rollback after injected failure;
- idempotent replay;
- concurrent job exclusion;
- preservation of leading-zero identifiers;
- source-row lineage for every target row.

## Release verification

Fresh evidence must include full tests, exact statement and branch coverage, compileall, repository validation, wheel build, wheel-content inspection, clean-environment installation, CLI smoke on synthetic input, protected smoke on the real source, and GitHub current-head checks. No predecessor-head, queued, pending, skipped-required, cancelled, absent, or synthetic-merge-only evidence can satisfy the release gate.
