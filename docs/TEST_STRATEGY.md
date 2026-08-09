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
- nested-table rejection;
- irregular rows;
- rowspan/colspan expansion, gaps, overlap, and trailing implicit rows;
- table, row, column, cell, and text limits.

### Inspection and CLI

- default empty header values;
- explicit header opt-in;
- source SHA/size;
- Content-Location scheme/hash without raw location;
- stable JSON errors and exit codes;
- module and console entry points.

### Repository and CI

- complete required documentation;
- full public docstrings;
- full-SHA Action pins;
- no committed MHTML;
- no prohibited Copilot token;
- NIM secret binding;
- OpenCode `share: false`;
- exact-head agent-branch quality execution;
- SHA-keyed push/PR concurrency;
- hash-locked binary-only quality dependency installation;
- dependency-integrity tests executed by `unittest discover`.

### Autonomous-maintenance contracts

Workflow contract tests require all of the following:

- open PRs select maintenance rather than disabling the loop;
- PR queue metadata carries exact head/base/writeability evidence;
- RCA and remediation-feasibility proof precede mutation;
- fork heads remain read-only and stale leases are discarded;
- only failed or cancelled Actions jobs may receive a bounded transient retry;
- an unchanged external blocker yields to the next open PR while execution capacity remains;
- at most one PR branch is actively mutated at a time;
- no second product PR is created while any PR remains open;
- `security-events: read` exists and `security-events: write` does not;
- PR source, comments, issues, reviews, logs, and artifacts are untrusted data rather than instructions;
- commands copied from untrusted content are prohibited;
- secrets and environment variables may not be printed, committed, commented, serialized, or transmitted;
- repository code, tests, package managers, build tools, and scripts run only through `cwl-safe-exec`;
- `cwl-safe-exec` creates a clean environment under a separate unprivileged Linux identity and removes model, GitHub, OIDC, and provider credentials;
- OpenCode denies arbitrary shell by default and only allows the wrapper plus bounded Git/GitHub control operations;
- direct interpreters, shells, environment inspection, network-fetch commands, and mutating raw `gh api` forms are not allowlisted;
- the repository does not duplicate the central merge scheduler and never approves, auto-merges, merges, tags, publishes, or releases.

## Secret-isolation verification

A focused operational rehearsal of the wrapper shall verify:

1. the effective UID differs from the privileged runner identity;
2. `NVIDIA_API_KEY`, `GH_TOKEN`, `GITHUB_TOKEN`, and OIDC request variables are absent;
3. the command starts inside `GITHUB_WORKSPACE` with only the explicit clean environment;
4. generated files are group-writable so the privileged control plane can commit verified changes;
5. attempts to invoke the wrapper outside the workspace fail before execution;
6. the installed wrapper is owned by `root:root` and not writable by the agent identity.

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

Fresh evidence must include full tests, exact statement and branch coverage, compileall, repository validation, wheel build, wheel-content inspection, clean-environment installation, CLI smoke on synthetic input, protected smoke on the real source, secret-isolation rehearsal, and GitHub current-head checks. No predecessor-head, queued, pending, skipped-required, cancelled, absent, or synthetic-merge-only evidence can satisfy the release gate.
