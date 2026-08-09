# Validation Report

**Validated:** 2026-08-09  
**Product version:** 0.1.0  
**Scope:** deterministic value-free MHTML inspection and work-conserving autonomous-maintenance contracts

## Evidence semantics

This report records reproducible repository evidence. It does not replace the live exact-head GitHub gate. Every commit, including documentation-only changes, must receive current-head quality, security, SAST, independent-review, and unresolved-thread evidence before merge or release.

Queued, pending, skipped-required, neutral-required, cancelled, absent, predecessor-head, stale-head, or synthetic-merge-only evidence is not passing.

## Test and coverage evidence

GitHub Repository Quality run `31309025537` executed the contributor head directly on Python 3.11, 3.12, 3.13, and 3.14. The Python 3.14 lane recorded:

```text
168 tests passed
825 production statements: 100%
320 production branches: 100%
Missing public production docstrings: 0
```

The same run completed:

```text
compileall: passed
repository contract validation: passed
wheel build: passed
```

Coverage includes the shipped package and production workflow helpers:

```text
scripts/hourly_product_gap.py:       112 statements, 42 branches, 100%
scripts/validate_repository.py:       75 statements, 42 branches, 100%
src/mhtml_etl_gateway/html_tables.py: 255 statements, 120 branches, 100%
src/mhtml_etl_gateway/mime_parser.py: 191 statements, 100 branches, 100%
total production:                    825 statements, 320 branches, 100%
```

## Parser security evidence

Regression-first tests prove that:

- an explicit RFC 2387 `start` resolves with zero/one/many cardinality before media-type acceptance;
- a missing `start` selects the first direct body part and never substitutes a later or nested HTML leaf;
- duplicate normalized Content-ID values fail closed across all descendant body entities;
- malformed structured MIME metadata and duplicate critical headers/parameters fail closed;
- source bytes, total MIME entities, MIME nesting depth, decoded HTML characters, tables, rows, columns, raw cells, projected cells, realized cells, and cell text are independently bounded;
- a one-leaf, 2,000-level MIME tree returns `mime_nesting_too_deep`, never an unstructured `RecursionError`;
- duplicate `rowspan` and `colspan` attributes are rejected case-insensitively;
- raw source-cell construction fails before allocating the first over-budget `_RawCell`;
- large span projections fail before logical `TableCell` allocation;
- realized normalized shape must equal the pre-allocation projection;
- a mismatched inert closing tag cannot escape an outer `script`, `style`, `noscript`, `template`, `iframe`, or `object` boundary;
- an HTML-void `embed` resource is ignored without suppressing following legitimate text;
- no browser, JavaScript, office, XML external-entity, database, or external-resource capability exists in the parser path.

## Public privacy and error evidence

Tests prove that the public report includes source SHA-256 and byte size, hashed Content-Location identity when present, table dimensions, header coordinate/source/count metadata, and fixed diagnostics while omitting:

- decoded HTML;
- data rows and header values;
- raw Content-ID and Content-Location;
- Content-Location scheme;
- source-controlled media type, charset, and transfer encoding;
- resource payloads and active-content text;
- local source path;
- sequential table identifiers.

The public Python API and CLI expose no header-value disclosure flag. The former CLI option is rejected through the fixed JSON argument-error contract. Future header access requires an authenticated, audited source-custody workflow and is not part of `InspectionReport`.

Expected failures serialize only a stable `error_code` and its approved fixed message. Caller-provided detail, configured limits, paths, MIME metadata, headers, cells, and payload text cannot be reflected through public error JSON.

The default report intentionally contains `source_hash_sha256`. This public validation document does not reproduce the protected real export's actual hash value.

## Autonomous-maintenance evidence

Workflow and configuration tests prove that:

- the hourly loop is execution-first and zero-narration;
- one completed patch, PR, failed remedy, queued check, review delay, rate limit, provider cooldown, or external approval dependency cannot terminate an invocation while safe repository-owned work remains;
- an unchanged external blocker receives one deduplicated record and yields to another PR, shared blocker, or proven-disjoint product slice;
- a gate-clean PR waiting for central merge does not idle the repository loop;
- only one branch is actively mutated at a time;
- at most one additional draft product PR may be created per invocation after refreshed non-overlap proof;
- fork heads remain read-only and exact-head leases are revalidated immediately before writes;
- only failed or cancelled Actions work can receive a bounded transient retry after source/configuration defects are excluded;
- queued, pending, skipped-required, absent, stale, or synthetic evidence is never treated as passing;
- local automation never approves, enables auto-merge, merges, tags, publishes, or releases.

Security tests additionally prove that:

- the root-owned secret-stripping wrapper is installed before repository gate code executes;
- repository-controlled code runs as `cwl-untrusted` with access only through the dedicated `cwl-workspace` group;
- model, GitHub, OIDC, OpenAI, Anthropic, Google, Strix, and OpenCode credentials are removed from the repository-code environment;
- gate code receives only the non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` marker;
- arbitrary shell and direct interpreter, package-manager, environment-inspection, and network-fetch commands are denied by default;
- raw `gh api` access is allowed only with an explicit GET method;
- no POST, PATCH, PUT, DELETE, field, raw-field, or input form is allowlisted;
- public OpenCode sharing is disabled in both workflow entry points and repository configuration;
- `COPILOT_GITHUB_TOKEN` is absent.

## Static and repository evidence

The deterministic repository validator confirms:

- required document inventory: complete;
- unresolved template-marker tokens: 0;
- mutable GitHub Action references: 0;
- both nested `.yml` and `.yaml` workflows are scanned;
- a missing hourly scheduler returns a machine-readable validation failure rather than a stack trace;
- prohibited Copilot credential references: 0;
- committed `.mhtml` or `.mht` artifacts: 0;
- NVIDIA NIM secret binding: present;
- OpenCode session sharing disabled;
- exact-head agent-branch quality execution enabled;
- push and pull-request quality concurrency keyed by exact head SHA.

CI dependency-integrity tests verify the reviewed SHA-256 hash lock, pip hash-checking and binary-only mode, exact contributor-head checkout, exact-head assertion, and YAML-safe block-scalar command syntax.

## Package evidence

The quality matrix builds:

```text
mhtml_etl_gateway-0.1.0-py3-none-any.whl
```

The package has no runtime dependency and includes:

- `mhtml_etl_gateway/py.typed`;
- the complete Apache License 2.0 under wheel license metadata;
- the console entry point;
- package version `0.1.0`.

A production release still requires current-head protected-branch merge, independent approval, fresh installed-wheel smoke evidence, SBOM, signed provenance, upgrade/rollback guidance, and release publication controls.

## Protected real-export evidence

A noncommitted operator-held MHTML export was inspected without publishing its filename, path, actual source hash, header values, or row values. The authorized aggregate receipt recorded:

```text
table_count: 1
row_count: 14
data_row_count: 13
column_count: 40
header_value_count: 40
document_diagnostics: identity_transfer_encoding, missing_related_type
table_diagnostics: positional_header
```

The current public report contract includes no raw path, location scheme, media classification, header value, or row value. Header count is structural metadata only; the values themselves remain unavailable through the public API and CLI.

## Release assessment

The implementation is a reviewable first pre-1.0 inspection slice. It is not yet a complete MHTML-to-PostgreSQL ETL product. Versioned protected schema proposals, approval, database migrations, transactional streamed `COPY FROM STDIN`, rejection quarantine, reconciliation, idempotent replay, tenancy, service APIs, deployment evidence, SBOM, and signed provenance remain future milestones.

Version `0.1.0` must not be released until the live exact PR head passes every organization-required check, independent approval, unresolved-thread policy, protected-branch merge, and release supply-chain gate.
