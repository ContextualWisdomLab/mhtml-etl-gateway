# ADR 0012: Value-free, versioned schema proposals before PostgreSQL loading

**Status:** Accepted for stacked M1 implementation  
**Date:** 2026-08-09

## Context

MHTML table headers and representative values are needed to propose PostgreSQL names and types. Those inputs may contain PII, customer identifiers, internal terminology, account values, and other protected business data. Copying raw values into PR comments, logs, schema-review tickets, or public proposal artifacts would violate the product's metadata-minimization boundary.

At the same time, an automatic loader must not infer DDL directly from unreviewed source text. Identifier-looking values with leading zeroes, compact dates, mixed types, binary floating-point values, invalid dates, and sparse samples all require conservative handling and explicit review evidence.

The initial parser slice deliberately has no database or loader authority. M1 therefore needs a standalone artifact that is useful for later protected approval and visualization without executing DDL or disclosing raw values.

## Decision

Create an in-process, side-effect-free `mhtml_etl_gateway.schema_proposal` package that accepts protected table labels, protected headers, and bounded representative sample tuples and emits a value-free `SchemaProposal`.

The proposal contains:

- exact SHA-256 identities for the table label and each source header;
- an ordered table fingerprint;
- per-column evidence fingerprints over typed, ordered canonical sample hashes;
- a proposal fingerprint binding algorithm, complete policy, ordered evidence, names, types, aggregates, and review decisions;
- deterministic multiword PostgreSQL target names;
- conservative PostgreSQL types;
- nullable recommendations and bounded aggregate evidence;
- fixed evidence and review codes;
- algorithm and policy versions.

The proposal contains no raw header, raw sample value, row payload, local path, DDL, SQL, database handle, URL, model output, or sequential public identifier.

### Naming

Derived target names use NFKC, camel/acronym splitting, Unicode-aware punctuation replacement, reserved-word protection, multiword suffixes, UTF-8 byte limits, reviewed enterprise aliases, and content-derived collision suffixes. Source identity hashes use the exact original UTF-8 label and do not normalize it.

### Types

The first policy can propose only `text`, `boolean`, `date`, `bigint`, and `numeric`.

- identifier semantics and significant leading zeroes always preserve `text`;
- booleans require native booleans or explicit boolean header semantics plus an exact policy vocabulary;
- dates require explicit date semantics and complete valid date evidence;
- datetimes never downcast to dates;
- `bigint` requires exact signed-64-bit integers;
- exact decimals and overflow integers use `numeric`;
- binary floats use `numeric` but require review;
- mixed, invalid, or empty evidence falls back to `text` with review where needed.

A sample cannot establish `NOT NULL`, so the first policy always proposes nullable columns and reports observed blank/nonblank counts separately.

### Authority

The module proposes only. It cannot:

- execute or generate DDL;
- connect to PostgreSQL;
- write a file;
- fetch a resource;
- invoke a model;
- approve a mapping;
- load or transform rows.

A later authenticated and audited protected workflow must approve a versioned artifact before a loader can consume it.

### Resource and error boundary

The policy bounds total columns, samples per column, label/header characters, canonical value characters, and identifier bytes. Unsupported objects and non-finite numbers fail closed. Very large integers and decimals are rejected before unbounded rendering.

All expected errors use stable codes and fixed messages. `ColumnEvidence.__repr__` is fixed and nonreflecting.

## Consequences

### Positive

- Schema review can occur without copying raw table data into ordinary control-plane surfaces.
- Mapping identity changes whenever source order, evidence, policy, target name, type, aggregate, or review decision changes.
- Leading-zero enterprise identifiers are protected from destructive numeric conversion.
- PostgreSQL naming complies with the multiword `snake_case` organization rule.
- The module is independently testable and usable before a database exists.
- A future `pg-erd-cloud` adapter can visualize proposal metadata without receiving source values.
- The proposal can later become an immutable input to approval, migration, and loader artifacts.

### Negative

- Header-derived normalized target names still reveal schema semantics; they remain governed metadata rather than anonymous output.
- Header and evidence hashes can support equality correlation and require access/retention controls.
- Conservative inference creates review work and may retain `text` where a domain expert later approves a narrower type.
- Representative samples cannot prove completeness, uniqueness, primary keys, foreign keys, check constraints, or non-nullability.
- The first implementation does not persist approvals or integrate with PostgreSQL.

## Rejected alternatives

### Direct DDL generation

Rejected because unreviewed source text would control database identifiers and types, and malformed or ambiguous evidence could become destructive schema changes.

### Raw headers and values in the proposal artifact

Rejected because proposal artifacts are likely to appear in logs, reviews, tickets, or CI output that do not share source-custody protections.

### LLM naming and type inference in M1

Rejected because the first proposal contract must be deterministic, offline, reproducible, and free of model/provider credentials. LLM assistance may be added only as an optional protected review layer that cannot overwrite deterministic evidence.

### Automatic `NOT NULL`, key, or relationship inference

Rejected because bounded representative samples cannot prove those invariants. Stronger source-system metadata and protected approval are required.

## Verification

The implementation must maintain:

- realistic SAP-shaped, Unicode, collision, leading-zero, date, boolean, numeric, null, mixed, and hostile input tests;
- order-, evidence-, and policy-sensitive fingerprint tests;
- no raw value/header reflection in JSON, repr, or fixed errors;
- static no-DDL/network/database/file-I/O tests;
- 100% production statement and branch coverage;
- 100% public docstrings;
- Python 3.11–3.14 exact-head CI;
- a draft stacked PR based on the deterministic inspection PR until the base reaches the protected branch.

## Affected artifacts

- `src/mhtml_etl_gateway/schema_proposal/`
- `tests/test_schema_proposal_*.py`
- `docs/SCHEMA_PROPOSAL_CONTRACT.md`
- future updates to PRD, TRD, API contract, data model, security, threat model, test strategy, roadmap, ADR index, research traceability, and CHANGELOG before retargeting or merge
