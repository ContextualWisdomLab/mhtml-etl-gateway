# ADR-0001: Non-rendering parser boundary

**Status:** Accepted

## Decision

Parse MIME and HTML as inert data. Do not use a browser, JavaScript engine, office application, CSS renderer, XML external-entity resolver, or network fetcher.

## Consequences

The attack surface and output are deterministic and testable. Browser-dependent visual tables are unsupported until a separate sandboxed adapter is justified and approved.
