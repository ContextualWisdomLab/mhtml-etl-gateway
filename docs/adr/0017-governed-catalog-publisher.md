# ADR-0017: Governed catalog publisher boundary

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** MHTML ETL Gateway maintainers

## Context

ADR-0015 established a deterministic, value-free catalog submission envelope,
but an envelope alone cannot tell an operator whether a remote catalog accepted
the planned graph writes. A buyer needs a bounded reconciliation artifact while
the gateway must not become an implicit credential, tenant-policy, retry, or
network authority.

## Decision

Add a transport-neutral `publish_catalog_submission` boundary. The caller owns
the `CatalogTransport` implementation and must provide explicit evidence of
actor authentication, tenant authorization, approval verification, and an
immutable audit reference. The gateway sends each validated request exactly once
through that transport and returns a receipt only when every response is:

1. an HTTP success status in the 2xx range;
2. explicitly marked accepted; and
3. bound to an opaque remote request identifier.

The receipt contains the envelope, target, audit reference, accepted count, and
safe per-request IDs/statuses, but never request bodies, source headers, sample
values, credentials, or provider error text. A transport error or partial
acceptance raises a fixed `CatalogPublisherError` containing only the failing
request index and accepted prefix count. The gateway performs no authentication,
authorization, TLS setup, retry, persistence, or network operation. A caller may
use RFC 9110 HTTP semantics, RFC 9457 problem details, and W3C Trace Context at
its adapter boundary without coupling those protocols to this library.

The publisher bounds a submission at 4,096 requests by default and rejects
unknown paths, methods, idempotency-key shapes, malformed responses, and
non-opaque remote identifiers before exposing a receipt.

## Consequences

- Standalone use remains deterministic and offline.
- Application-owned adapters can prove remote acceptance and reconcile partial
  outcomes without passing protected values through the gateway.
- Provider authentication, retry/idempotency policy, trace propagation, audit
  persistence, and tenant/approval policy remain independently testable.
- The receipt is evidence of the adapter response, not proof that the caller's
  identity or approval system is intrinsically trustworthy.

## Verification

`tests/test_semantic_catalog_publisher.py` covers successful 2xx/204 responses,
all governance evidence gates, request ordering, bounded request counts, invalid
request and response shapes, remote rejection, provider exceptions, partial
acceptance, fixed safe errors, and absence of request bodies from receipts.

## References

- Fielding, R., Nottingham, M., & Reschke, J. (2022). *HTTP semantics* (RFC
  9110). Internet Engineering Task Force. https://doi.org/10.17487/RFC9110
- Nottingham, M., Wilde, E., & Dalal, S. (2023). *Problem details for HTTP
  APIs* (RFC 9457). Internet Engineering Task Force.
  https://doi.org/10.17487/RFC9457
- World Wide Web Consortium. (2021). *Trace context*.
  https://www.w3.org/TR/trace-context/
