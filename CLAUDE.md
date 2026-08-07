# MHTML ETL Gateway Context

Read `AGENTS.md` first. This repository implements a deterministic enterprise ingestion boundary, not a browser automation tool.

## Architecture invariants

1. Immutable source bytes and SHA-256 identity are the root of lineage.
2. MIME structure validation, root resolution, HTML decoding, table extraction, schema proposal, and PostgreSQL loading remain separate modules.
3. The parser never renders, executes active content, launches office software, or performs network access.
4. RFC 2387 root selection is deterministic: explicit `start` wins; otherwise the first body part is the root.
5. Duplicate critical headers/parameters, parser defects, ambiguous IDs, malformed spans, and exhausted budgets fail closed.
6. Missing `multipart/related` `type` is accepted only as a diagnosed enterprise compatibility deviation; a present type must match the selected root.
7. Default inspection output contains no cell-derived values, including header values, and never exposes raw Content-Location.
8. Schema inference proposes; a policy or human approves before persistent DDL.
9. Loading flows through immutable raw, staging, normalized, and audit layers with reconciliation.
10. PII remains usable through strong access and lifecycle controls rather than destructive masking.
11. Database object names contain at least two words, preferably `snake_case`.
12. Central `.github` workflows own review, security, and merge automation.
13. Every behavior change follows TDD and preserves 100% production line, branch, and docstring coverage.

## Current implementation

The current package safely inspects MHTML and produces nonreflecting source/table metadata. PostgreSQL writes, schema inference, API services, and external connectors are later bounded slices; do not claim those capabilities before exact-head evidence exists.
