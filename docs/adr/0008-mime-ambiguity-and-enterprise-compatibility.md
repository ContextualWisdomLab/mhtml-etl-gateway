# ADR 0008: MIME ambiguity and enterprise compatibility

**Status:** Accepted
**Date:** 2026-08-07

## Context

RFC 2387 requires a `type` parameter and defines `start` or the first body part as the compound-object root. Enterprise exporters may omit `type` or emit a nonstandard Content-Transfer-Encoding such as `text/html`. MIME libraries can also collapse duplicate parameters or attach parser defects to malformed structured headers.

## Decision

Security-critical ambiguity fails closed: parser defects, duplicate critical headers, duplicate `boundary`/`start`/`type`, ambiguous Content-ID, non-HTML explicit roots, non-HTML default roots, and contradictory declared type are rejected.

Two observed deviations remain available with diagnostics:

- missing related `type` after the selected root is independently proven to be HTML;
- unknown transfer encoding treated as identity bytes and marked `identity_transfer_encoding`.

## Consequences

Standards conformance and practical enterprise availability are distinguished explicitly. Compatibility never changes root selection, enables execution/fetch, or suppresses evidence.
