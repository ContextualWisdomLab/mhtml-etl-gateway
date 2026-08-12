# ADR-0020: Local schema-proposal boundary

**Status:** Accepted
**Date:** 2026-08-12
**Decision owners:** ContextualWisdomLab

## Context

The gateway already had a deterministic proposal engine, but operators had to
write a private adapter that extracted table headers and rows and then import
the internal proposal module. That gap blocked the first buyer-visible path
from an MHTML artifact to a reviewable schema, while exposing the temptation to
add raw headers or values to public inspection output.

## Decision

Add `propose_schema_from_mhtml` and the `mhtml-etl-gateway propose` command.
Both reuse the existing bounded MHTML/table pipeline and `propose_schema`
engine. Headers and rows remain in protected process memory; the only output is
the existing value-free `SchemaProposal` JSON contract. The wrapper marks the
complete extracted columns as complete for nullability evidence. It performs no
database, network, authentication, LLM, connector submission, or file-write
operation.

The command is a local source-custody tool, not an authenticated service. The
caller owns authorization, access, retention, export approval, and any later
Semantic Data Portal or pg-erd-cloud transport.

## Consequences

Operators can produce a deterministic review artifact directly from a customer
MHTML export, making the proposal/catalog/visualization ecosystem usable as a
standalone module. The gateway still does not claim schema approval, remote
acceptance, or data reconciliation. Proposal JSON remains sensitive because
hashes permit equality correlation and therefore requires caller-owned controls.

## Traceability

- Product: [PRD](../PRD.md), [ROADMAP](../ROADMAP.md)
- Design: [ARCHITECTURE](../ARCHITECTURE.md), [UML](../UML.md), [ERD](../ERD.md)
- Contract: [API_CONTRACT](../API_CONTRACT.md), [SCHEMA_PROPOSAL_CONTRACT](../SCHEMA_PROPOSAL_CONTRACT.md)
- Security: [THREAT_MODEL](../THREAT_MODEL.md), [OPERABILITY](../OPERABILITY.md)
- Verification: [TEST_STRATEGY](../TEST_STRATEGY.md), [VALIDATION_REPORT](../VALIDATION_REPORT.md)
- Standard: [RESEARCH_TRACEABILITY](../RESEARCH_TRACEABILITY.md), [APA 7th references](../doctoring/REFERENCES.md)
