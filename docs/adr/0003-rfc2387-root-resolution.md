# ADR-0003: RFC 2387 root resolution

**Status:** Accepted

## Decision

For `multipart/related`, resolve an explicit `start` parameter to exactly one `text/html` Content-ID. If `start` is absent, select the first HTML leaf. Missing or duplicate explicit roots fail closed.

## Consequences

Decoy parts cannot silently replace the producer-declared root. Some malformed producers require a documented compatibility profile instead of an implicit fallback.
