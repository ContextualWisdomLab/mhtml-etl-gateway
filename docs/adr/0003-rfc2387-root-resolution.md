# ADR-0003: RFC 2387 root resolution

**Status:** Accepted  
**Date:** 2026-08-09

## Context

A `multipart/related` document can identify its authoritative root with the `start` parameter. When `start` is absent, RFC 2387 defines the first direct body part as the root. Searching for the first HTML leaf instead would silently skip an earlier non-HTML or nested multipart root and permit semantic substitution.

Duplicate normalized `Content-ID` values are ambiguous even when only one duplicate is HTML. Root selection must therefore classify identifier cardinality before media-type acceptance.

## Decision

For `multipart/related`:

1. If `start` is present, normalize its Content-ID and resolve it across every descendant body entity.
2. Zero matches fail with `missing_html_root`.
3. More than one match fails with `ambiguous_html_root` before media-type validation.
4. The unique match must be a non-multipart `text/html` body entity.
5. If `start` is absent, select the first direct body part exactly; reject it unless it is non-multipart `text/html`.
6. Never skip to a later HTML part or descend to a nested HTML leaf on the default-root path.
7. A present RFC 2387 `type` parameter must match the selected root. A missing `type` is accepted only through the documented enterprise compatibility diagnostic.

## Consequences

- Decoy, reordered, or nested body parts cannot silently replace the compound object's root.
- Root selection is deterministic and independent of MIME part ordering after an explicit identifier becomes ambiguous.
- Malformed producers require an explicit compatibility decision rather than an implicit HTML fallback.
- Some documents a browser might render permissively are rejected because ingestion integrity takes precedence over visual recovery.

## References

- Levinson, E. (1998). *The MIME Multipart/Related content-type* (RFC 2387). RFC
  Editor. https://doi.org/10.17487/RFC2387
  https://www.rfc-editor.org/rfc/rfc2387
