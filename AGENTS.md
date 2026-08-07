# Agent Development Rules

## Product boundary

MHTML ETL Gateway converts untrusted enterprise MHTML into governed PostgreSQL-ready assets. Keep source custody, MIME parsing, table extraction, schema proposal, approval, loading, lineage, and connectors modular so each module works independently and inside a larger CWL MSA ecosystem.

## Non-negotiable data safety

- Never execute HTML, JavaScript, CSS, macros, browser extensions, office applications, or embedded active content.
- Never fetch external, `cid:`, `file:`, or relative resources while parsing.
- Never modify raw source bytes; the exact SHA-256 is the lineage root.
- Never commit customer MHTML, row values, header values, internal paths, or protected report artifacts to this public repository.
- Never silently discard a MIME part, table, source row, logical cell, validation error, or load error.
- Fail closed on parser defects, duplicate critical MIME metadata, root ambiguity, malformed spans, resource-budget exhaustion, and inconsistent lineage.
- Default outputs and logs must not reflect source-controlled identifiers, charsets, transfer encodings, media types, Content-Location values, paths, or cell values.
- Cell-derived header values require explicit operator opt-in and protected handling.

## PII and regulated data

Do not destroy operational PII through default masking when that would make the business process unusable. Preserve authorized values behind tenant isolation, encryption, least privilege, purpose limitation, row/column authorization, retention and deletion controls, export approval, and immutable audit evidence. Public diagnostics, logs, metrics, and default reports remain metadata-only.

## Database conventions

Every database schema, table, view, materialized view, index, constraint, sequence, function, trigger, role, and policy name must contain at least two words. Prefer `snake_case`. External identifiers use opaque UUIDv7 values; never expose sequential numeric identifiers.

## Engineering workflow

- Use test-driven development for every behavior change: observe RED, implement minimal GREEN, then refactor.
- Production statement and branch coverage must remain 100%.
- Every shipped public module, class, function, method, property, error, and contract needs a beginner-readable docstring.
- Tests must include business-shaped SAP exports, malformed MIME, duplicate metadata, encodings, Korean text, rich text, spans, hostile size/shape inputs, privacy nonreflection, reconciliation, and PostgreSQL rollback behavior as those layers appear.
- Update PRD, TRD, architecture, ADRs, security, threat model, test strategy, operability, doctoring references, research traceability, compliance mapping, and CHANGELOG whenever their contracts change.
- Pin every GitHub Action to a full commit SHA.
- Scheduled model work uses `NVIDIA_NIM_API_KEY`; never use `COPILOT_GITHUB_TOKEN`.
- Public-repository OpenCode sessions must set `share: false`.
- Do not duplicate organization review or merge scheduling; `ContextualWisdomLab/.github` is the central source of truth.

## Merge and release

Review every open PR on its exact head, reproduce actionable findings with failing tests, repair them, rerun all checks, and merge only when current-head checks, independent approval, unresolved-thread policy, security evidence, and branch rules permit it. Update `CHANGELOG.md`, version metadata, SBOM/provenance, and release notes before any release.
