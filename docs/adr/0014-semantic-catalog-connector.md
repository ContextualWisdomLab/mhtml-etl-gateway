# ADR-0014: Value-free Semantic Data Portal connector

**Status:** Accepted
**Date:** 2026-08-11

## Context

The gateway can produce a deterministic, value-free PostgreSQL schema proposal,
but a buyer still needs a governed handoff into a semantic catalog. The
ContextualWisdomLab Semantic Data Portal accepts graph node and edge requests
for dataset and column discovery. Coupling the parser to a remote HTTP service
would weaken standalone operation, credential boundaries, and deterministic
testing.

## Decision

Add an in-process `semantic_catalog_connector` module that converts an existing
`SchemaProposal` into a deterministic `SemanticCatalogManifest` containing
request-compatible dataset/column nodes and `contains_column` edges. The module
will:

1. preserve source and proposal fingerprints while never copying protected
   headers or sample values;
2. expose the current `/graph/nodes` and `/graph/edges` endpoint paths as data;
3. leave authentication, actor identity, tenant policy, approval, retries, and
   network transport to the caller;
4. remain usable as a standalone library and as an MSA module;
5. use a content-derived manifest ID for idempotent handoff and replay;
6. map future JSON-LD publication to DCAT 3 only after a separately governed
   publisher contract is implemented.

## Consequences

Positive consequences:

- MHTML schema evidence becomes discoverable by the semantic catalog without
  placing raw enterprise values in the catalog payload.
- Identical proposals produce identical manifests, enabling safe retry and
  deduplication at the caller-owned transport boundary.
- The connector can be tested without network credentials and cannot silently
  bypass schema approval.
- The parser, loader, portal, and future `pg-erd-cloud` integration remain
  independently deployable modules.

Trade-offs:

- The gateway does not submit requests or report remote acceptance in this
  slice; an authenticated integration service is still required.
- Node properties are a portal-compatible internal contract, not yet a complete
  DCAT/JSON-LD publisher.

## Verification

`tests/test_semantic_catalog_connector.py` covers endpoint shapes, deterministic
and order-sensitive identity, validation, empty-schema behavior, value-free
serialization, and all public value-object serializers. The repository quality
gate verifies Python 3.11–3.14 compatibility and exact 100% statement/branch
coverage.

## References

- World Wide Web Consortium. (2024). *Data Catalog Vocabulary (DCAT)—Version 3*.
  https://www.w3.org/TR/vocab-dcat-3/
- ContextualWisdomLab. (2026). *Semantic Data Portal graph node and edge request
  contracts* [Source code]. GitHub.
