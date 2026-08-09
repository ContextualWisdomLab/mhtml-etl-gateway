# Changelog

All notable changes follow Keep a Changelog, and versions follow Semantic Versioning.

## [Unreleased]

### Added

- Dependency-free Python package for bounded MHTML MIME parsing.
- RFC 2387 explicit-root and first-body default-root resolution.
- Non-rendering top-level table extraction with deterministic span normalization.
- Immutable SHA-256 source lineage and metadata-only inspection CLI.
- Explicit local opt-in for header-value output while keeping every cell-derived value private by default.
- Content-Location scheme classification and SHA-256 identity without raw location disclosure.
- Synthetic SAP-style, hostile-input, CLI, workflow, privacy, MIME-cardinality, and documentation tests.
- Repository PRD, TRD, architecture, data, API, security, threat, test, operating, compliance, roadmap, ADR, research-traceability, and APA 7th doctoring baselines.
- Exact-head Python 3.11–3.14 quality workflow.
- Default-branch-only hourly OpenCode autonomous loop using NVIDIA NIM, exact-head PR maintenance, and a durable single-flight `agent-task` lease for empty-queue product work.

### Changed

- Public inspection reports no longer include normalized header text unless the operator explicitly requests it.
- RFC 2387 `type` omission is recorded as `missing_related_type` for known enterprise exports; contradictory declared types fail closed.
- Unknown enterprise Content-Transfer-Encoding values remain an identity-decoding compatibility path with a generic diagnostic.
- The hourly OpenCode workflow explicitly disables session sharing for the public repository.
- An open PR now selects deterministic RCA-and-repair mode instead of disabling the hourly loop; product PR creation remains blocked until the PR queue is empty.

### Fixed

- Default-root selection validates the first direct `multipart/related` body part and never substitutes a nested HTML leaf.
- Explicit `start` duplicates are classified as ambiguous before media-type validation, independent of MIME part order.
- Duplicate critical headers and duplicate `boundary`, `start`, or `type` parameters fail closed before structured parsing can collapse them.
- Defective structured MIME headers that affect root selection fail closed.
- Mismatched closing tags cannot escape an outer inert `script`, `style`, `noscript`, or `template` boundary.
- Span overlap, trailing rowspans, and later-column rowspan gaps are normalized deterministically.
- Public errors no longer echo source paths, Content-ID values, charsets, transfer encodings, or declared media types.
- The autonomous scheduler no longer treats review or check latency as a blanket no-op when repository-owned fixes or bounded job reruns are feasible.

### Security

- Active content, browser rendering, XML entity resolution, office execution, and external resource retrieval are structurally excluded.
- Source, MIME part, HTML, table, row, column, cell, cell-text, and normalized-cell budgets fail closed.
- Default reports and logs exclude data rows, header values, raw Content-Location, and embedded resource payloads.
- Customer MHTML artifacts are prohibited from the public repository.
- PII protection uses access, encryption, tenant, lifecycle, export, and audit controls instead of destructive default masking.
- Repository quality CI installs its coverage tool from a reviewed SHA-256 hash lock in pip hash-checking and binary-only mode, and pull-request quality jobs explicitly check out and verify the exact contributor head rather than GitHub's synthetic merge ref.
- PR maintenance validates exact head/base metadata, treats fork heads as read-only, discards stale leases before writes, and never synthesizes approval or weakens central merge gates.
