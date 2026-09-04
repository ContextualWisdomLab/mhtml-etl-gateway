# ADR-0001: Non-rendering parser boundary

**Status:** Accepted

## Decision

Parse MIME and HTML as inert data. Do not use a browser, JavaScript engine, office application, CSS renderer, XML external-entity resolver, or network fetcher.

## Consequences

The attack surface and output are deterministic and testable. Browser-dependent visual tables are unsupported until a separate sandboxed adapter is justified and approved.

## References

The following locator names the MHTML aggregate-document format that this
decision parses as inert data. It does not add a renderer, network fetcher, or
other product method.

- Palme, J., Hopmann, A., & Shelness, N. (1999). *MIME encapsulation of
  aggregate documents, such as HTML (MHTML)* (RFC 2557). RFC Editor.
  https://doi.org/10.17487/RFC2557
  https://www.rfc-editor.org/rfc/rfc2557
