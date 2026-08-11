# Semantic Data Portal connector

## Purpose

The gateway now has a standalone connector boundary from a value-free
`SchemaProposal` to the graph-ingestion request shapes used by
`ContextualWisdomLab/semantic-data-portal`. This closes the buyer gap between
reviewing an MHTML-derived schema and making the approved structure discoverable
in a semantic catalog.

The connector is intentionally not an HTTP client. It returns a deterministic
manifest; an authenticated application-owned adapter decides when and how to
submit its `nodes` to `/graph/nodes` and its `edges` to `/graph/edges`.

```mermaid
flowchart LR
    A[Protected MHTML headers and bounded samples] --> B[SchemaProposal]
    B --> C[SemanticCatalogManifest]
    C --> D[Steward approval and caller-owned auth]
    D --> E[semantic-data-portal /graph/nodes]
    D --> F[semantic-data-portal /graph/edges]
    C --> G[No raw headers, samples, network, DB, or file writes]
```

## Python contract

```python
from mhtml_etl_gateway import build_semantic_catalog_manifest

manifest = build_semantic_catalog_manifest(
    proposal,
    catalog_name="SAP VOC export",
)
payload = manifest.to_dict()
```

The result contains:

- deterministic `manifest_id`, connector contract version, source SHA-256, and
  schema-proposal ID;
- one `dataset` graph node and one `column` node per proposed column;
- `contains_column` edges connecting the dataset node to its columns;
- proposal types, nullability, aggregate counts, review reasons, and header
  fingerprints only;
- endpoint paths that match the current Semantic Data Portal graph API.

The `catalog_name` is steward-provided display metadata. It is not copied from
protected sample values. The connector does not receive or reconstruct raw
headers: normalized target names and fingerprints come from the existing
value-free proposal contract.

## Security and operating boundary

The manifest is not an approval. A caller must perform authentication,
authorization, tenant selection, idempotency handling, retry policy, and
steward approval before submitting requests. The caller must attach the portal's
`actor` field and transport credentials at the final network boundary; neither
is persisted in this package's manifest.

The connector performs no database connection, DDL, LLM call, HTTP request,
filesystem write, browser rendering, or external-resource retrieval. It can be
embedded as a library or used by a future MSA connector service without changing
the deterministic parser path.

## Governed submission handoff

When an application is ready to publish an approved manifest, it can make the
authority explicit without adding a network client to this package:

```python
from mhtml_etl_gateway import (
    CatalogPublisherEvidence,
    build_semantic_catalog_submission_envelope,
    publish_catalog_submission,
)

envelope = build_semantic_catalog_submission_envelope(
    manifest,
    tenant_id="tenant_cwl_production",
    actor="svc_catalog_publisher",
    approval_reference="approval_2026_08_11_001",
)

evidence = CatalogPublisherEvidence(
    actor_authenticated=True,
    tenant_authorized=True,
    approval_verified=True,
    immutable_audit_reference="audit_2026_08_11_001",
)

receipt = publish_catalog_submission(envelope, publisher, evidence)
```

The envelope records a deterministic handoff ID, the manifest ID, contract and
target metadata, claimed tenant and approval context, and ordered node/edge
`POST` plans. Each plan has a stable idempotency key scoped by tenant and
approval reference and adds the explicit `actor` field expected by the portal.
The tenant and approval references remain envelope-level governance metadata
rather than graph-node properties. Envelope and request IDs are correlation and
deduplication evidence only: `publisher` remains responsible for verifying actor
authentication, authorizing the tenant, verifying the approval, binding
credentials and TLS, retrying safely, and writing immutable audit evidence. The
publisher requires each adapter response to be an explicitly accepted 2xx
response with an opaque remote request ID and returns a safe
`CatalogPublicationReceipt`; it never stores request bodies or provider error
text. A partial outcome is reported with a bounded accepted prefix so the caller
can reconcile it using its own idempotency and audit policy. The envelope and
receipt are not proof that the caller's identity or approval system is
intrinsically trustworthy.

`publisher` is a caller-owned implementation of the transport protocol. A
minimal adapter returns an accepted `CatalogTransportResponse` after applying
its own authentication, authorization, TLS, trace propagation, retry, and audit
rules. The gateway performs no HTTP, authentication, retry, persistence, or
network operation.

## Interoperability mapping

Semantic Data Portal's `dataset` and `column` nodes form a graph-native
representation. A future JSON-LD export may map the dataset node to DCAT 3
`dcat:Dataset`, its schema proposal to a versioned catalog record, and its
SHA-256 to a checksum/distribution identity. This slice keeps that mapping
explicit and local rather than claiming full DCAT serialization before a
governed catalog publisher exists.

## Evidence

- `tests/test_semantic_catalog_connector.py` verifies endpoint-compatible node
  and edge shapes, deterministic identity, order sensitivity, empty-schema
  behavior, validation, and absence of protected values.
- The full repository test suite remains at exactly 100% statement and branch
  coverage.
- Upstream API alignment was checked against the Semantic Data Portal
  `GraphNodeRequest` and `GraphEdgeRequest` contracts on 2026-08-11.

The governing decisions are [ADR-0014](adr/0014-semantic-catalog-connector.md),
[ADR-0015](adr/0015-governed-catalog-handoff.md), and
[ADR-0017](adr/0017-governed-catalog-publisher.md).
