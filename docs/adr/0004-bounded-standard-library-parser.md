# ADR-0004: Bounded standard-library parser

**Status:** Accepted

## Decision

The initial runtime uses Python's standard-library `email` and `html.parser` modules behind explicit resource budgets and immutable contracts.

## Consequences

There are no runtime dependencies and the trust core is small. Producer-specific HTML recovery and streaming optimizations require later evidence-driven extensions.
