# Product Requirements Document: MHTML ETL Gateway

**Version:** 0.1
**Status:** Accepted implementation baseline
**Date:** 2026-08-07

## Product vision

MHTML ETL Gateway converts enterprise MHTML exports into governed, queryable PostgreSQL assets while preserving exact source evidence. It addresses exports that humans can open but data platforms cannot safely operationalize because MIME root selection, table structure, encoding, types, lineage, and active-content boundaries are implicit.

The product is an ingestion control plane rather than an HTML-to-table convenience script. Its full product boundary covers immutable evidence, deterministic extraction, privacy-preserving inspection, schema governance, validation, reconciliation, loading, observability, audit, and modular integration.

## Buyer problem

Enterprise teams regularly receive SAP ALV, spreadsheet web-archive, browser-save, and legacy reporting exports in MHTML. Manual conversion creates five recurring risks:

1. the wrong MIME body part is treated as the source table;
2. row, column, encoding, and span semantics are silently changed;
3. customer data and internal paths leak through logs and diagnostic artifacts;
4. repeated imports create duplicate or irreconcilable records;
5. no durable evidence links a PostgreSQL row back to exact source bytes and a reviewed mapping.

## Users

- **Data engineer:** repeatably inspects and imports exports without a bespoke parser per report.
- **Data steward:** reviews proposed names, types, constraints, and sensitive-data policies before activation.
- **Business analyst:** receives stable PostgreSQL assets with documented provenance and validation outcomes.
- **Security/compliance operator:** proves source custody, access, change approval, retention, and incident evidence.
- **Platform integrator:** embeds the parser, inspection contract, or future loader as an independent module.

## Product principles

- Raw bytes are immutable evidence.
- Untrusted content is parsed, never rendered or executed.
- Ambiguity fails closed; known enterprise deviations are explicit diagnostics rather than silent acceptance.
- Default output minimizes disclosure without destroying the authorized operational dataset.
- Schema inference proposes; a human or policy approves.
- Every loaded row is reconcilable to source, table, and source-row coordinates.
- Standalone operation and MSA composition are equally supported.

## Current P0 release slice: deterministic inspection

The `0.1.0` implementation shall:

- accept bounded standalone `text/html` and `multipart/related` input;
- reject parser defects and duplicate security-critical MIME metadata;
- follow RFC 2387 `start`, or use the first body part when `start` is absent;
- require an explicit root to resolve uniquely across all leaf parts and to be `text/html`;
- validate a present RFC 2387 `type` against the selected root;
- accept a missing `type` only with `missing_related_type` diagnostic for observed enterprise compatibility;
- decode declared charset strictly, then BOM, then strict UTF-8 fallback;
- diagnose nonstandard transfer encodings accepted as identity bytes;
- extract only top-level tables and reject nested-table ambiguity;
- normalize `rowspan` and `colspan` into a rectangular logical grid;
- suppress active and non-visible template content;
- enforce bounded source, MIME, HTML, table, row, column, cell, and cell-text budgets;
- emit source hash/size, root type, protected location metadata, dimensions, header-source metadata, counts, and diagnostics;
- omit all cell-derived values, including header text, by default;
- expose header values only through explicit local opt-in;
- use stable error codes and messages that do not reflect attacker-controlled values.

## P1: governed schema proposals

The next product slice shall produce versioned, reviewable PostgreSQL schema proposals without executing DDL. A proposal includes source header fingerprint, normalized multiword `snake_case` name, proposed data type, nullability evidence, date/number/code ambiguity, confidence, policy findings, and reviewer decision.

No automatic inference may reinterpret identifier-like values with leading zeroes as numbers without explicit policy evidence.

## P2: PostgreSQL loading

The loader shall use transaction-safe staging and `COPY FROM STDIN`, then reconcile:

- extracted source row count;
- accepted and rejected row counts;
- target row count;
- per-column conversion errors;
- source-row coordinates;
- import/source/schema versions;
- rollback outcome.

A load cannot be marked complete while reconciliation is unbalanced.

## P3: enterprise operation

The operational product shall add asynchronous jobs, idempotency, tenant boundaries, object storage, OpenTelemetry, audit export, SSO/SCIM integration points, retention and legal-hold policy, disaster recovery, signed release provenance, SBOM, and controlled connectors.

## PII and sensitive business data

The product shall not apply destructive default masking when an authorized workflow requires exact customer, employee, supplier, document, or account values. Protection uses tenant isolation, encryption, least privilege, purpose limitation, row/column authorization, just-in-time export approval, retention, deletion/hold controls, and immutable audit. Public logs, metrics, diagnostics, default reports, and issue artifacts remain metadata-only.

## Ecosystem priorities

1. `ContextualWisdomLab/.github`: inherited review, security, supply-chain, and merge governance.
2. `pg-erd-cloud`: reviewed schema proposal and lineage visualization contracts.
3. `naruon`: authenticated ingestion notifications and governed handoff artifacts.
4. `pg-llm-batch`: optional batch enrichment after deterministic ingestion, never in the trusted parser path.
5. `contextual-orchestrator`: optional policy/review orchestration after deterministic evidence exists.

## Success metrics

- source-to-report determinism: 100% for identical bytes/configuration;
- default cell-value disclosure: 0 values;
- raw Content-Location disclosure: 0 values;
- lineage completeness: 100% of accepted loads;
- reconciliation balance: 100% before completion;
- production statement/branch/public-docstring coverage: 100%;
- malformed/ambiguous inputs that are silently accepted: 0;
- required current-head merge gates bypassed: 0.

## Release acceptance

A release requires exact-head CI, 100% line and branch coverage, complete public docstrings, package/wheel smoke tests, realistic and hostile fixtures, security review, independent approval, unresolved-thread closure, SBOM/provenance, CHANGELOG/version alignment, and evidence that no customer artifact entered the repository.
