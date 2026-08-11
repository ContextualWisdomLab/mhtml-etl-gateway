# ADR 0011: Value-free, content-addressed schema proposals

**Status:** Proposed  
**Date:** 2026-08-09

## Context

The inspection layer intentionally excludes source headers and cell values from its public report. Schema design nevertheless requires protected access to those values. Reintroducing headers through a public CLI flag would bypass authentication, audit, retention, and output controls. Generating DDL directly from untrusted source text would also create schema-injection and irreversible type-coercion risk.

The product therefore needs an intermediate artifact that is useful to a data steward but contains no raw protected value and has no authority to mutate PostgreSQL.

## Decision

Introduce `mhtml_etl_gateway.schema_proposal` as a pure in-process module.

The caller supplies:

- exact immutable source SHA-256;
- ordered protected headers;
- bounded string/null evidence per column;
- whether the evidence is a complete column or only a sample;
- a versioned resource and inference policy.

The module emits a content-addressed `SchemaProposal` containing:

- source and ordered-table fingerprints;
- source-header hashes;
- unique multiword `snake_case` target names;
- conservative PostgreSQL type proposals;
- nullability and bounded aggregate evidence;
- explicit review reasons;
- algorithm version and proposal identity.

It never serializes raw headers or sample values and never performs DDL, database access, network access, file writes, or LLM calls.

### Conservative inference

- Identifier semantics and leading zeroes force `text`.
- Boolean inference accepts only exact `true`/`false` vocabulary.
- Date inference requires valid supported values and protected header semantics.
- Integral values within signed 64-bit range may become `bigint`.
- Larger integral and fixed-point values may become `numeric` with explicit evidence.
- Ambiguous, locale-formatted, exponential, mixed, unsupported, empty, and sample-limited evidence remains conservative and reviewable.

### Naming

Derived naming uses Unicode NFKC only on the naming channel, leaving exact source fingerprints unchanged. It supports acronym/camel boundaries, explicit validated SAP aliases, reserved-word protection, digit-leading protection, opaque collision suffixes, and PostgreSQL's 63-byte UTF-8 identifier limit. Persistent sequential identifiers are not introduced.

## Consequences

- A data engineer gains a deterministic handoff between inspection and future governance.
- Raw source values remain inside source custody.
- Proposal equality and change can be audited by hash.
- Generated proposals still require human or policy approval.
- The initial alias and type policy is deliberately narrow and versioned; expanding it changes proposal identity.
- No migration or load capability can be claimed from this module alone.
- Future UI and service work must treat proposal artifacts and source/header hashes as sensitive even though raw values are absent.
