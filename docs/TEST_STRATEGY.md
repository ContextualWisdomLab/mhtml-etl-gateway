# Test Strategy

## Principles

Every behavior change follows RED-GREEN-REFACTOR. Tests assert externally meaningful behavior and fail closed on ambiguity. Production statement, branch, and public-docstring coverage are exact 100% gates, not approximate targets.

## Current suites

### MIME

- standalone and multipart roots;
- explicit start, missing start target, non-HTML target, and cross-media duplicate IDs;
- ambiguity classification independent of MIME part ordering;
- first-direct-body default-root enforcement and nested-root rejection;
- missing, matching, and contradictory related type;
- parser defects, duplicate singleton headers, duplicate critical parameters;
- quoted semicolons, escaped quotes, nested comments, and malformed parameter fields;
- strict charset/BOM/UTF-8 paths;
- nonstandard transfer-encoding diagnostic;
- source, total MIME entity, and MIME depth limits;
- extreme nested multipart input that would otherwise raise `RecursionError`;
- stable `mime_nesting_too_deep` conversion;
- generic nonreflecting error text.

The extreme nesting regression uses 2,000 nested multipart entities with one HTML leaf. It must produce `MhtmlGatewayError` with `mime_nesting_too_deep`, never an unstructured Python recursion exception. A separate low-depth fixture verifies the configurable `max_mime_depth` boundary.

### HTML tables

- semantic and positional headers;
- Korean and rich text;
- block and line-break normalization;
- exact script/style/noscript/template suppression nesting;
- mismatched closing-tag resistance;
- iframe/object descendant suppression without allowing void `embed` to swallow following text;
- nested-table rejection;
- irregular rows;
- rowspan/colspan expansion, gaps, overlap, and trailing implicit rows;
- table, row, column, cell, and text limits.

### Inspection and CLI

- default empty header values;
- source SHA/size;
- Content-Location hash without raw location;
- stable JSON errors and exit codes;
- argument-construction errors isolated from inspection-layer domain errors;
- module and console entry points.

### Schema proposals and semantic catalog handoff

- realistic SAP-shaped protected columns become normalized multiword names and
  value-free proposal evidence;
- identical proposals produce identical catalog manifest IDs;
- reordering protected columns changes the manifest identity and preserves
  ordered graph mapping;
- dataset/column nodes and `contains_column` edges match the Semantic Data
  Portal request shapes;
- raw source headers and representative values are absent from serialized
  manifests;
- empty-schema and invalid steward display-name boundaries fail closed;
- actor-, tenant-, and approval-bound handoff envelopes produce stable IDs and
  unique per-request idempotency keys;
- every handoff request carries the explicit actor while tenant/approval context
  remains envelope-level metadata;
- invalid governance references and control characters fail closed;
- connector generation performs no HTTP, database, LLM, or file operation.

### Database identifier and mapping contract

- single-token headers become stable `_field` names and single-token table
  inputs become `_table` names;
- suffixes remain present at the 63-byte PostgreSQL boundary;
- direct one-word, mixed-case, overlong, and punctuation-bearing identifiers
  fail before DDL or row writes;
- realistic mapped DDL contains only multiword table/column names and emits
  `COMMENT ON COLUMN` in the same setup transaction;
- the fixed catalog uses `load_status_code` and its replay-safe legacy rename
  migration is emitted without caller-controlled SQL text.
- integer inference keeps signed BIGINT bounds and classifies larger realistic
  values as `NUMERIC`;
- arbitrary `TableSchema` PostgreSQL types fail before DDL generation;
- live connection, SQL operation, load, and unsafe-identifier failures expose
  fixed messages without DSNs, SQL, identifiers, or provider detail.

### Governed catalog publisher

- complete submissions accept realistic `201` responses and `204` responses
  only when the caller provides all authentication, tenant, approval, and
  immutable-audit evidence;
- every receipt is value-free, ordered, idempotency-correlated, and carries an
  opaque remote request ID;
- invalid evidence, request paths/methods/keys, request limits, response status,
  explicit acceptance flags, and remote IDs fail closed;
- provider exceptions, remote rejection, and partial accepted prefixes produce
  fixed safe errors without provider bodies or request bodies;
- the publisher performs no authentication, HTTP, retry, persistence, or file
  operation and reaches 100% statement and branch coverage.

### Repository and CI

- complete required documentation;
- full public docstrings;
- full-SHA Action pins;
- no committed MHTML;
- no prohibited Copilot token;
- NIM secret binding;
- direct OpenCode `SHARE="false"` in both agent modes and repository `share="disabled"`;
- exact-head agent-branch quality execution;
- SHA-keyed push/PR concurrency;
- hash-locked binary-only quality dependency installation;
- dependency-integrity and pytest-style behavior tests executed by the same
  hash-locked `pytest` coverage command used in CI.

### Autonomous-maintenance contracts

Workflow contract tests require all of the following:

- open PRs select maintenance rather than disabling the loop;
- PR queue metadata carries exact head/base/writeability evidence;
- RCA and remediation-feasibility proof precede mutation;
- fork heads remain read-only and stale leases are discarded;
- only failed or cancelled Actions jobs may receive a bounded transient retry;
- a blocked action blocks only that action, never the invocation;
- one completed patch, PR, failed remedy, queued check, review delay, provider cooldown, or external approval dependency cannot terminate the run while executable work remains;
- an unchanged external blocker yields to the next open PR while execution capacity remains;
- a gate-clean PR waiting for central merge does not stall the next executable item;
- shared CI, tooling, dependency, standards, and documentation blockers are part of the executable queue;
- existing open PRs do not blanket-prohibit one verified, disjoint buyer-visible slice;
- at most one additional draft product PR may be created per invocation after refreshed non-overlap proof;
- no overlapping files, schemas, migrations, generated artifacts, dependencies, or writer ownership are permitted across concurrent PR work;
- at most one branch is actively mutated at a time;
- routine output is empty and inventory, plan, status, RCA-essay, progress, and recap narration is prohibited;
- scheduler/prompt edits, issue updates, commits, PR publication, and central merge handoff are intermediate events rather than stop conditions;
- the hourly recurrence is continuation rather than intentional deferral;
- a run stops only after finite execution capacity is genuinely exhausted or a fresh full-queue scan proves every remaining item non-actionable under current authority;
- after PR work is exhausted, the same invocation continues through issues, document/ADR completeness, release readiness, buyer-visible gaps, and ecosystem integration;
- routine next-step questions are prohibited when live evidence can resolve the choice;
- `security-events: read` exists and `security-events: write` does not;
- PR source, comments, issues, reviews, logs, and artifacts are untrusted data rather than instructions;
- commands copied from untrusted content are prohibited;
- secrets and environment variables may not be printed, committed, commented, serialized, or transmitted;
- the root-owned wrapper is installed before the repository-owned gate script executes;
- the gate receives only a non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` marker and runs through `cwl-safe-exec`;
- repository code, tests, package managers, build tools, and scripts run only through `cwl-safe-exec`;
- `cwl-safe-exec` creates a clean environment under a separate unprivileged Linux identity and removes model, GitHub, OIDC, and provider credentials;
- `cwl-untrusted` receives workspace access only through the dedicated `cwl-workspace` group and never inherits the runner default group;
- OpenCode denies arbitrary shell by default and only allows the wrapper plus bounded Git/GitHub control operations;
- direct interpreters, shells, environment inspection, network-fetch commands, and mutating raw `gh api` forms are not allowlisted;
- the repository does not duplicate the central merge scheduler and never approves, auto-merges, merges, tags, publishes, or releases.

### Privileged OpenCode runner supply chain

The active `pytest` suite verifies the exact executable that will receive model and repository authority:

- the upstream composite action is absent from the hourly workflow;
- mutable nested `actions/cache@*`, latest-release lookup, and remote installer piping are absent;
- version `1.18.15` is committed in the workflow;
- the Linux x64 release URL is immutable and versioned;
- SHA-256 `d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c` is committed and checked with strict mode;
- the archive must contain exactly one `opencode` entry;
- extraction does not preserve archive ownership or permissions;
- `opencode --version` must equal `1.18.15` before the binary enters the command path;
- the installation step contains no model, GitHub, or OIDC credential binding;
- both agent modes call the verified binary directly with `USE_GITHUB_TOKEN="false"`, private sharing, and the approved NVIDIA NIM model;
- shell line-continuation normalization is tested so formatting changes do not weaken or spuriously fail the executable contract.

A future version change must update the version, digest, upstream evidence, tests, ADR, security/threat/operability documents, doctoring references, and CHANGELOG in one reviewed PR. Missing or conflicting digest evidence is a failing test and blocks the upgrade.

## Secret-isolation verification

A focused operational rehearsal of the wrapper shall verify:

1. the effective UID differs from the privileged runner identity;
2. `NVIDIA_API_KEY`, `NVIDIA_NIM_API_KEY`, `GH_TOKEN`, `GITHUB_TOKEN`, and OIDC request variables are absent;
3. the only NIM-related value visible to repository gate code is the non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` marker;
4. `COPILOT_GITHUB_TOKEN` is neither configured nor allowlisted;
5. the command starts inside `GITHUB_WORKSPACE` with only the explicit clean environment;
6. generated files are `cwl-workspace` group-writable so the privileged control plane can commit verified changes;
7. the unprivileged identity is not a member of the runner's default group;
8. attempts to invoke the wrapper outside the workspace fail before execution;
9. the installed wrapper is owned by `root:root` and not writable by the agent identity.

The rehearsal uses sentinel variable names and set/unset checks only. It never prints a real secret value.

## Realistic test policy

Synthetic fixtures model SAP-style codes with leading zeroes, compact dates, Korean text, rich cell content, nonstandard transfer encoding, and positional headers. A protected real export can be used in local/operator validation but is never committed and no value is printed. Its regression evidence is limited to exact source hash, byte size, aggregate table dimensions, diagnostic codes, and absence of raw protected metadata.

## Future loader tests

A PostgreSQL test container shall verify:

- migration up/down behavior;
- multiword naming contract;
- tenant RLS;
- streamed COPY;
- source/accepted/rejected/target count reconciliation;
- conversion-error quarantine;
- transaction rollback after injected failure;
- idempotent replay;
- concurrent job exclusion;
- preservation of leading-zero identifiers;
- source-row lineage for every target row.

## Release verification

Fresh evidence must include full tests, exact statement and branch coverage, compileall, repository validation, wheel build, wheel-content inspection, clean-environment installation, CLI smoke on synthetic input, protected smoke on the real source, secret-isolation rehearsal, verified OpenCode archive/version checks, and GitHub current-head checks. No predecessor-head, queued, pending, skipped-required, cancelled, absent, or synthetic-merge-only evidence can satisfy the release gate.
