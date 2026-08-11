# Validation Report

**Validated:** 2026-08-09  
**Product version:** 0.1.0  
**Scope:** deterministic value-free MHTML inspection, work-conserving autonomous maintenance, and verified OpenCode runner delivery

## Current 0.3.0 implementation addendum

The historical evidence below remains preserved for the original inspection
baseline. The current merged main implementation also includes versioned
value-free schema proposals, `COMMENT ON COLUMN` mapping support, and the
Semantic Data Portal connector boundary. In the current integration worktree on
2026-08-11, Python 3.14 evidence for the governed catalog handoff candidate is:

```text
310 tests passed
3 tests skipped
30 subtests passed
2,681 production statements: 100%
936 production branches: 100%
```

`tests/test_semantic_catalog_connector.py` proves deterministic dataset/column
graph manifests, endpoint-compatible node/edge shapes, order-sensitive identity,
raw-value absence, and caller-owned transport boundaries. The connector creates
no network, database, LLM, or file side effect. The handoff tests also prove
actor-, tenant-, and approval-bound envelope identity, explicit actor request
bodies, tenant- and approval-scoped idempotency keys, strict surrounding-
whitespace rejection, and invalid-context rejection. The candidate passes
repository validation, compileall, full-repository Ruff checks, and wheel
build. Database identifier tests additionally prove multiword canonicalization,
63-byte suffix preservation, fail-closed direct SQL names, realistic
`COMMENT ON COLUMN` output, the replay-safe `load_status_code` catalog
migration, signed-BIGINT overflow classification as `NUMERIC`, fixed PostgreSQL
DDL type allow-listing, and nonreflecting connection/operation/load/identifier
failures. Its merge and release claims remain subject to fresh exact-head
GitHub evidence.

## Evidence semantics

This report records reproducible repository evidence. It does not replace the live exact-head GitHub gate. Every commit, including documentation-only changes, must receive current-head quality, security, SAST, independent-review, and unresolved-thread evidence before merge or release.

Queued, pending, skipped-required, neutral-required, cancelled, absent, predecessor-head, stale-head, or synthetic-merge-only evidence is not passing.

## Test and coverage evidence

GitHub Repository Quality run `31313275676` executed contributor head `91174648e0c0324979767c0a9c918cff15962261` directly on Python 3.11, 3.12, 3.13, and 3.14 and completed successfully. The Python 3.11 lane recorded:

```text
182 tests passed
842 production statements: 100%
326 production branches: 100%
Missing public production docstrings: 0
```

The same exact-head matrix completed:

```text
compileall: passed
repository contract validation: passed
wheel build: passed
```

Coverage includes the shipped package and production workflow helpers:

```text
scripts/hourly_product_gap.py:        112 statements,  42 branches, 100%
scripts/validate_repository.py:       75 statements,  42 branches, 100%
src/mhtml_etl_gateway/html_tables.py: 255 statements, 120 branches, 100%
src/mhtml_etl_gateway/mime_parser.py: 189 statements, 100 branches, 100%
total production:                     842 statements, 326 branches, 100%
```

The documentation commit containing this report does not convert predecessor-head evidence into current-head evidence. Its own GitHub checks remain independently required.

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

- success is defined as material repository progress rather than inventory or narration;
- the hourly recurrence is continuation rather than intentional deferral;
- scheduler or prompt edits, issue updates, commits, PR publication, and central merge handoff are intermediate events rather than stop conditions;
- one completed patch, PR, failed remedy, queued check, review delay, rate limit, provider cooldown, or external approval dependency cannot terminate an invocation while safe repository-owned work remains;
- a blocked action blocks only that action, not the invocation;
- an unchanged external blocker receives one deduplicated record and yields to another PR, shared blocker, or proven-disjoint product slice;
- a gate-clean PR waiting for central merge does not idle the repository loop;
- after PR work is exhausted, the same invocation continues through issues, document/ADR completeness, release readiness, buyer-visible gaps, and ecosystem integration;
- the only normal stop conditions are genuine finite execution-budget exhaustion or a fresh full-queue proof that every remaining item is non-actionable under current authority;
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

## Verified OpenCode runner evidence

The exact-head test suite also proves that the privileged scheduler no longer uses the upstream composite installer path. The workflow contract requires:

```text
OpenCode version: 1.18.15
asset: opencode-linux-x64.tar.gz
SHA-256: d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c
archive entries: exactly one (`opencode`)
runtime version: exactly 1.18.15
```

The following are prohibited and regression-tested:

- `anomalyco/opencode/github@...` composite execution;
- mutable nested `actions/cache@...` use;
- latest-release lookup;
- `curl | bash` or any remote installer script;
- digest-free fallback;
- trusted cross-run executable cache;
- model, GitHub, or OIDC credential binding during installation.

The install step verifies platform, immutable URL, digest, archive shape, extraction ownership/permission policy, and exact runtime version before the directory enters `GITHUB_PATH`. Only later selected agent-mode steps receive `NVIDIA_API_KEY`, the fixed NVIDIA NIM model, `SHARE="false"`, and `USE_GITHUB_TOKEN="false"`.

The digest is recorded by the upstream generated Homebrew formula at commit `a72a2bfe3b4114ca10a9012c23f1b3f31924b22e`. This is release-distribution evidence, not a claim of an independent cryptographic builder attestation. The residual boundary is documented in ADR-0011, the threat model, and the upgrade/rollback runbook.

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
- OpenCode session sharing disabled in both direct modes;
- exact-head agent-branch quality execution enabled;
- push and pull-request quality concurrency keyed by exact head SHA.

CI dependency-integrity tests verify the reviewed SHA-256 hash lock, pip hash-checking and binary-only mode, exact contributor-head checkout, exact-head assertion, and YAML-safe block-scalar command syntax.

## Package evidence

The quality matrix builds:

```text
mhtml_etl_gateway-0.1.0-py3-none-any.whl
```

The Python 3.11 lane produced a wheel of 22,055 bytes with build-instance SHA-256 `c8a4a8f84786ae9cf72e1c68e8562b052cdc8eb3d1f650855659ad3c140cade1`. This build-instance digest is evidence for that run, not yet a reproducible-release claim.

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
