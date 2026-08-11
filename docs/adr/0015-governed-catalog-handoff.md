# ADR-0015: Governed Semantic Data Portal handoff envelope

**Status:** Accepted
**Date:** 2026-08-11

## Context

ADR-0014 creates a deterministic value-free catalog manifest, but a production
publisher still needs an auditable boundary for tenant selection, actor
identity, approval evidence, and safe retries. Leaving that context implicit
invites anonymous portal writes or ambiguous replay semantics. Putting HTTP,
credentials, or approval decisions in the parser would compromise standalone
operation and make the deterministic path harder to test.

## Decision

Add `semantic_catalog_handoff` with a
`build_semantic_catalog_submission_envelope` function. It will:

1. require non-empty, control-character-free actor context and bounded opaque
   tenant/approval references;
2. emit ordered portal-compatible node and edge `POST` plans with explicit
   actor fields;
3. derive stable per-request idempotency keys and an envelope ID from the
   manifest plus tenant- and approval-scoped governance context;
4. keep tenant and approval references at the handoff boundary rather than
   persisting them in graph-node properties;
5. perform no authentication, authorization, HTTP, retry, database, file, or
   LLM operation;
6. remain independently usable by an MSA publisher or an embedded caller.

## Consequences

Positive consequences:

- A caller can carry the claimed tenant, actor, and approval context alongside
  a proposed catalog write before it crosses the network boundary. The envelope
  itself is not proof of actor authentication, tenant authorization, approval
  verification, or remote acceptance; the publisher must verify and audit each
  condition separately.
- Retries are safe to coordinate per node/edge request without treating an
  envelope construction as proof of remote acceptance.
- The parser remains value-free and standalone; exact business values are not
  introduced merely to make governance auditable.

Trade-offs:

- A separate publisher still must verify approval state, bind credentials and
  TLS, enforce tenant authorization, retry, and record remote responses.
- Tenant and approval systems remain integration-specific until a service API
  and shared identity contract are implemented.

## Verification

`tests/test_semantic_catalog_connector.py` covers deterministic envelope
identity, actor-bearing request bodies, tenant- and approval-scoped idempotency
keys, raw-value absence, direct request serialization, whitespace rejection,
and invalid governance context. The repository quality gate verifies Python
3.11–3.14 compatibility and exact 100% statement/branch coverage.

## References

- World Wide Web Consortium. (2024). *Data Catalog Vocabulary (DCAT)—Version 3*.
  https://www.w3.org/TR/vocab-dcat-3/
- ContextualWisdomLab. (2026). *Semantic Data Portal graph node and edge request
  contracts* [Source code, commit e48aa13c4af7a4875d4b53e6a60b50405c265a2f;
  `src/sdp/api.py`, `src/sdp/graph_models.py`]. GitHub.
  https://github.com/ContextualWisdomLab/semantic-data-portal/tree/e48aa13c4af7a4875d4b53e6a60b50405c265a2f/src/sdp
