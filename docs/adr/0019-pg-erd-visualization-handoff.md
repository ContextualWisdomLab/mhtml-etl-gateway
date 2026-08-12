# ADR-0019: Value-free pg-erd-cloud visualization handoff

**Status:** Accepted
**Date:** 2026-08-12
**Decision owners:** ContextualWisdomLab
**Supersedes:** None

## Context

The gateway already produces a deterministic, value-free `SchemaProposal` and
can hand it to the Semantic Data Portal. Buyers still need a visible schema
review surface before approving a PostgreSQL design. `pg-erd-cloud` exposes a
design-first DBML conversion route that can create a schema snapshot without
requiring the gateway to own network credentials or diagram persistence.

## Decision

Add a small `pg_erd_connector` module that converts a `SchemaProposal` into a
deterministic `PgErdVisualizationPlan` for `POST /api/dbml/convert`.

The plan will:

1. use the existing table and identifier normalization boundary;
2. map only the existing proposal types to DBML type names;
3. represent non-nullability as DBML `[not null]`;
4. exclude raw headers, sample values, comments, notes, defaults, records, and
   guessed relationships;
5. leave authentication, transport, retry, approval, persistence, and remote
   acceptance to the caller.

## Consequences

The standalone library gains a directly consumable visualization request and a
clear MSA connector seam. The same proposal can be sent independently to the
Semantic Data Portal and pg-erd-cloud without duplicating source custody or
releasing PII into diagram metadata.

The first slice visualizes one proposed table only. Multi-table relationships,
review decisions, and persisted diagram reconciliation require a later,
versioned contract; the connector must not infer them from names.

## Traceability

- Product: [PRD](../PRD.md), [ROADMAP](../ROADMAP.md)
- Design: [ARCHITECTURE](../ARCHITECTURE.md), [UML](../UML.md), [ERD](../ERD.md)
- Security: [THREAT_MODEL](../THREAT_MODEL.md), [OPERABILITY](../OPERABILITY.md)
- Verification: [TEST_STRATEGY](../TEST_STRATEGY.md), [VALIDATION_REPORT](../VALIDATION_REPORT.md)
- Contract: [PG_ERD_CONNECTOR](../PG_ERD_CONNECTOR.md)
