# Product Requirements Document: MHTML ETL Gateway

**Version:** 0.3
**Status:** Accepted implementation baseline with explicit future service boundaries
**Date:** 2026-08-11

## Product vision

Version `0.1.0` currently provides deterministic, privacy-preserving inspection of untrusted enterprise MHTML exports. It proves which MIME body is authoritative, extracts bounded top-level table structure without rendering or execution, and emits a value-free structural report tied to the immutable source bytes.

The product is intended to evolve into an enterprise ingestion control plane that produces governed, queryable PostgreSQL assets. Schema governance, validation, transactional loading, reconciliation, service APIs, tenant storage, and external connectors remain future slices until exact-head implementation evidence exists.

## Buyer problem

Enterprise teams regularly receive SAP ALV, spreadsheet web-archive, browser-save, and legacy reporting exports in MHTML. Manual conversion creates five recurring risks:

1. the wrong MIME body part is treated as the source table;
2. row, column, encoding, and span semantics are silently changed;
3. customer data and internal paths leak through logs and diagnostic artifacts;
4. repeated imports create duplicate or irreconcilable records;
5. no durable evidence links a future PostgreSQL row back to exact source bytes and a reviewed mapping.

## Users

- **Data engineer:** inspects exports deterministically today and will later import approved mappings without a bespoke parser per report.
- **Data steward:** will review proposed names, types, constraints, and sensitive-data policies before activation.
- **Business analyst:** will receive stable PostgreSQL assets with documented provenance and validation outcomes after the loader milestone.
- **Security/compliance operator:** proves source custody, data minimization, change approval, retention, and incident evidence.
- **Platform integrator:** embeds the current parser and inspection contract or future loader as independent modules.

## Product principles

- Raw bytes are immutable evidence.
- Untrusted content is parsed, never rendered or executed.
- Ambiguity fails closed; known enterprise deviations are explicit diagnostics rather than silent acceptance.
- Default output contains structural evidence without cell-derived values or raw source-controlled metadata.
- A future schema engine proposes; a human or policy approves before DDL or loading.
- Every future loaded row must reconcile to source, table, and source-row coordinates.
- Standalone operation and MSA composition are equally supported.
- Product claims never exceed exact-head implemented and verified behavior.

## Current P0 release slice: deterministic inspection

The `0.1.0` implementation shall:

- accept bounded standalone `text/html` and `multipart/related` input;
- reject parser defects and duplicate security-critical MIME metadata;
- resolve exactly one root: when RFC 2387 `start` is present, match it uniquely across descendant body entities; otherwise select the first direct body part;
- require the selected root to be non-multipart `text/html` and never skip to a later or nested HTML part;
- validate a present RFC 2387 `type` against the selected root;
- accept a missing `type` only with a `missing_related_type` diagnostic for observed enterprise compatibility;
- decode declared charset strictly, then BOM, then strict UTF-8 fallback;
- diagnose nonstandard transfer encodings accepted as identity bytes;
- extract only top-level tables and reject nested-table ambiguity;
- normalize `rowspan` and `colspan` into a rectangular logical grid;
- reject duplicate, invalid, overlapping, or resource-exhausting span declarations before large logical allocation;
- suppress active and container-style embedded content while treating void resource elements according to HTML semantics;
- enforce bounded source, MIME entity, MIME depth, decoded HTML, table, raw-cell, row, column, normalized-cell, and cell-text budgets;
- emit source SHA-256 and byte size, hashed Content-Location identity when present, table dimensions, header coordinate/source/count metadata, and fixed diagnostics;
- omit all cell-derived values, including header text, from the public Python and CLI report;
- use stable error codes and approved fixed messages that do not reflect attacker-controlled values;
- perform no network, browser, office, XML-entity, database, or external-resource operation.

Header values required by future schema governance must remain inside an authenticated source-custody workflow with authorization, audit, retention, and protected output. That workflow is not part of the current public inspection API or CLI.

## P1: governed schema proposals and catalog handoff

The next product slice shall produce versioned, reviewable PostgreSQL schema proposals without executing DDL. A protected proposal workflow includes source-header fingerprints, normalized multiword `snake_case` names, proposed data types, nullability evidence, date/number/code ambiguity, confidence, policy findings, reviewer decisions, and immutable source lineage.

No automatic inference may reinterpret identifier-like values with leading zeroes as numbers without explicit policy evidence. Source headers and sample values must never be copied into public logs, issues, or default reports.

The current P1 integration slice also emits a deterministic, value-free
Semantic Data Portal manifest. It exposes dataset/column graph nodes and
`contains_column` edges for caller-owned authenticated submission, while
keeping network, tenant, approval, and transport authority outside the parser.

## P2: PostgreSQL loading

The loader shall use transaction-safe staging and streamed `COPY FROM STDIN`, then reconcile:

- extracted source row count;
- accepted and rejected row counts;
- target row count;
- per-column conversion errors;
- source-row coordinates;
- import/source/schema versions;
- rollback outcome.

A load cannot be marked complete while reconciliation is unbalanced.

## P3: enterprise operation

The operational product shall add asynchronous jobs, idempotency, tenant boundaries, encrypted object storage, OpenTelemetry, audit export, SSO/SCIM integration points, retention and legal-hold policy, disaster recovery, signed release provenance, SBOM, and controlled connectors.

## PII and sensitive business data

The product shall not apply destructive default masking when an authorized workflow requires exact customer, employee, supplier, document, or account values. Protection uses tenant isolation, encryption, least privilege, purpose limitation, row/column authorization, just-in-time export approval, retention, deletion/hold controls, and immutable audit. Public logs, metrics, diagnostics, inspection reports, and issue artifacts remain metadata-only.

## Ecosystem priorities

1. `ContextualWisdomLab/.github`: inherited review, security, supply-chain, and merge governance.
2. `semantic-data-portal`: current value-free schema-proposal catalog handoff; future steward and ontology workflow.
3. `pg-erd-cloud`: future reviewed schema proposal and lineage visualization contracts.
4. `naruon`: future authenticated ingestion notifications and governed handoff artifacts.
5. `pg-llm-batch`: optional post-ingestion enrichment, never in the trusted parser path.
6. `contextual-orchestrator`: optional policy/review orchestration after deterministic evidence exists.

## Success metrics

### Current inspection slice

- source-to-report determinism: 100% for identical bytes and limits;
- default cell-value disclosure: 0 values;
- raw Content-Location disclosure: 0 values;
- active-content execution and external fetch: 0 operations;
- malformed or ambiguous inputs silently accepted: 0;
- production statement, branch, and public-docstring coverage: 100%;
- required current-head merge gates bypassed: 0.

### Future ingestion slices

- lineage completeness: 100% of accepted loads;
- reconciliation balance: 100% before completion;
- duplicate completed imports for one tenant/idempotency key: 0;
- unauthorized cross-tenant disclosure: 0.

## Release acceptance

A release requires exact-head CI, 100% line and branch coverage, complete public docstrings, package and installed-wheel smoke tests, realistic and hostile fixtures, security review, independent approval, unresolved-thread closure, SBOM and provenance appropriate to the release stage, CHANGELOG/version alignment, and evidence that no customer artifact entered the repository.
