# Architecture Decision Record Index

This directory is the canonical record of material architectural and governance decisions for MHTML ETL Gateway.

The **status declared inside each ADR is authoritative**. This index deliberately does not duplicate that status value, preventing a status transition from creating two competing sources of truth. A status change must edit the ADR itself and, when the decision is superseded, add a reciprocal `Superseded by` / `Supersedes` link.

## Current decisions

| ADR | Decision |
|---|---|
| [ADR-0001](0001-non-rendering-parser-boundary.md) | Parse MHTML and HTML as inert data; no rendering, active-content execution, or external retrieval. |
| [ADR-0002](0002-immutable-source-identity.md) | Bind processing and lineage to immutable source identity. |
| [ADR-0003](0003-rfc2387-root-resolution.md) | Resolve the authoritative `multipart/related` root using explicit RFC 2387 semantics. |
| [ADR-0004](0004-bounded-standard-library-parser.md) | Use a bounded standard-library parser boundary with explicit resource limits and fail-closed behavior. |
| [ADR-0005](0005-metadata-only-default-output.md) | Keep the default public inspection artifact metadata-only and nonreflecting. |
| [ADR-0006](0006-central-workflow-inheritance.md) | Inherit organization-central review/security/merge governance instead of duplicating privileged policy. |
| [ADR-0007](0007-hourly-product-development-loop.md) | Use a bounded hourly autonomous product-development loop with NVIDIA NIM/OpenCode and central merge authority. |
| [ADR-0008](0008-mime-ambiguity-and-enterprise-compatibility.md) | Fail closed on MIME ambiguity while isolating explicitly documented enterprise compatibility deviations. |
| [ADR-0009](0009-nonreflecting-metadata-surfaces.md) | Prevent attacker-controlled MIME/table values from entering public metadata and error surfaces. |
| [ADR-0010](0010-work-conserving-autonomous-execution.md) | Make autonomous execution work-conserving so one blocked lane cannot terminate safe repository-owned work. |
| [ADR-0011](0011-verified-opencode-runner.md) | Verify the exact OpenCode release archive and CLI version before exposing model or repository credentials. |
| [ADR-0013](0013-fork-read-only-maintenance.md) | Enforce fork PR triage in a separate read-only job with no OIDC or repository-write authority. |
| [ADR-0014](0014-semantic-catalog-connector.md) | Emit deterministic value-free Semantic Data Portal graph manifests without taking network or approval authority. |
| [ADR-0015](0015-governed-catalog-handoff.md) | Bind catalog submission plans to explicit tenant, actor, approval, and idempotency context while keeping transport authority outside the gateway. |
| [ADR-0016](0016-multiword-database-identifiers.md) | Enforce descriptive multiword database identifiers at inference, DDL, catalog, and dynamic-SQL boundaries. |
| [ADR-0017](0017-governed-catalog-publisher.md) | Publish governed request plans through a caller-owned transport and record bounded remote-acceptance receipts without source values. |
| [ADR-0018](0018-streamed-postgresql-copy.md) | Stream typed PostgreSQL rows with `COPY FROM STDIN` inside the existing atomic load transaction. |

## Status vocabulary

Use these values inside ADRs:

- **Proposed** — decision is under review and must not be treated as an implemented contract.
- **Accepted** — decision is the governing design rule; implementation maturity is tracked separately in code, tests, roadmap, and PR evidence.
- **Deprecated** — retained for historical compatibility but should not drive new implementation.
- **Superseded** — replaced by a named later ADR; both records remain for traceability.
- **Rejected** — evaluated and intentionally not adopted.

`Accepted` never means “already implemented.” For example, an accepted decision about a future PostgreSQL loader can govern the planned implementation while the current protected branch still contains only the deterministic inspection package. PRD/TRD/Architecture/UML/ERD/ROADMAP must label that distinction explicitly.

## When an ADR is required

Create or update an ADR when a change materially alters any of the following:

- trust or authority boundary;
- source-custody/privacy model;
- deterministic parser or ambiguity policy;
- public API/data contract or versioning policy;
- database schema strategy, tenancy, lineage, or retention model;
- schema-approval or loader authority;
- deployment topology or MSA boundary;
- security/compliance control strategy;
- autonomous writer/reviewer/merge authority;
- ecosystem dependency that changes standalone behavior;
- release, rollback, or migration contract.

Minor refactors and implementation details that preserve an accepted decision do not need a new ADR.

## Traceability contract

Every new ADR must be discoverable from this index and should identify affected PRD/TRD/Architecture/API/Data Model/Security/Test/Operability sections. Implementation PRs should cite the governing ADR in their description or traceability record. If tests prove a decision-specific invariant, keep that mapping in `docs/RESEARCH_TRACEABILITY.md`, `docs/VALIDATION_REPORT.md`, or a dedicated requirements-to-evidence matrix rather than relying on prose in the PR alone.

## Documentation review rule

A material decision change is incomplete until this directory, the relevant canonical documents, diagrams, tests, and CHANGELOG agree. Documentation-only completion must not be used to claim a planned service, migration, database object, security control, or release artifact is already operational.
