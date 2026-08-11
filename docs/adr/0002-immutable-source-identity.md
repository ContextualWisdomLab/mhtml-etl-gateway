# ADR-0002: Immutable source identity

**Status:** Accepted

## Decision

Identify every source by SHA-256 of exact bytes and never overwrite the raw artifact. Reprocessing creates a new run linked to the same artifact.

## Consequences

Lineage, idempotency, audit, and replay are possible. Object storage cost increases and retention must be policy-controlled.
