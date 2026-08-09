# Operability

## Current library operation

Version `0.1.0` is a synchronous local inspection library and CLI. It has no listening port, database credential, background worker, browser runtime, office dependency, or network egress.

Operators control resource budgets through `ParseLimits` and the CLI source-byte limit. Programmatic budgets cover source bytes, all descendant MIME entities, MIME depth, decoded HTML, tables, rows, columns, raw cells, projected and realized normalized cells, and cell text. Every budget is a positive non-boolean integer.

## Logging

Applications may log stable error and diagnostic codes, source SHA-256, source byte size, table dimensions, parser version, duration, and an opaque correlation ID. They must not log:

- local source paths;
- raw Content-ID or Content-Location;
- location scheme;
- media type, charset, or transfer encoding supplied by the source;
- header or row values;
- decoded HTML or resource payloads;
- MIME boundary values;
- exception chains containing source-controlled detail.

The public package emits no operational logs by itself. The CLI writes one success JSON object to stdout or one fixed-message error JSON object to stderr.

## Current health and capacity model

The package has no service health endpoint. A caller determines availability by importing the package or invoking the CLI. Service liveness/readiness contracts belong to a later authenticated service milestone.

Resource limits are per document and independent of deployment capacity. A future worker pool will add tenant queue quotas, concurrency limits, backpressure, hard process-memory limits, cancellation, and dead-letter recovery. Large input does not justify disabling parser budgets.

Capacity tests must measure at least:

- source bytes and decoded HTML expansion ratio;
- total MIME entities and nesting depth;
- raw source-cell count;
- projected normalized cells before allocation;
- realized table rows and columns;
- cell-text characters;
- wall time and peak RSS;
- expected failure code at each boundary.

## Metrics for a future service

- intake count and bytes;
- parse success/failure by stable code;
- MIME entity and depth rejection counts;
- decoded-character, raw-cell, projected-cell, and realized-cell rejection counts;
- document/table dimensions by bounded histogram;
- compatibility diagnostic counts;
- duration and peak memory;
- schema-review queue depth;
- load and reconciliation outcomes;
- retry, rollback, cancellation, and dead-letter counts;
- tenant-scoped SLOs without raw customer labels.

OpenTelemetry is the future observability baseline. Trace attributes use opaque IDs and hashes rather than values.

## Candidate service SLOs

These are future targets, not current guarantees:

- accepted-job durability: 99.99%;
- parser service availability excluding rejected unsafe input: 99.9%;
- reconciliation-complete load success for valid approved inputs: 99.9%;
- unauthorized cross-tenant disclosure: 0;
- lost immutable source after acknowledgement: 0;
- unbalanced load marked complete: 0.

## Backup and disaster recovery

The current library stores nothing. A future service must back up immutable source objects, approved schema artifacts, audit events, and PostgreSQL state in encrypted, versioned storage. Restore tests must prove lineage and reconciliation integrity. Legal-hold and deletion semantics must be explicit for payload and retained audit evidence.

## Incident response

Incident classes include:

- source or derived-value disclosure;
- tenant-boundary failure;
- data corruption;
- active-execution or external-fetch boundary violation;
- parser CPU/memory exhaustion;
- unavailable ingestion;
- model, GitHub, OIDC, or database credential exposure;
- unauthorized branch mutation;
- supply-chain compromise;
- false passing evidence or stale-head merge evidence.

A future service may disable intake or loading while preserving read-only audit and source custody. The repository scheduler may disable model dispatch while preserving read-only GitHub evidence collection.

## Hourly autonomous-development operation

The scheduled workflow is repository maintenance, not product runtime. It becomes active only when present on the protected default branch.

### Execution model

Runs are serialized by a repository-wide non-cancelling concurrency group. Each invocation maintains a live executable queue and repeats:

```text
fresh evidence
→ highest-value safe action
→ RCA only as needed
→ realistic failing test
→ minimal mutation
→ exact-head verification
→ central merge handoff
→ next executable item
```

Routine status narration is not an outcome. A completed patch, newly opened PR, failed first remedy, queued check, reviewer delay, rate limit, provider cooldown, or external approval dependency does not end the invocation while another safe repository-owned action exists.

### PR maintenance

When PRs are open, the deterministic gate validates the complete queue and uses the lowest-numbered PR only as an initial cursor. It emits exact head SHA, head/base refs, queue size, and same-repository writeability.

The maintenance agent:

- refetches live head/base, reviews, threads, statuses, check runs, jobs/logs, code scanning, and branch policy;
- proves a remedy is permitted, feasible, and capable of changing the blocker;
- uses realistic failing tests for repository defects;
- reruns only failed or cancelled Actions work after source/configuration faults are excluded;
- treats fork heads as read-only;
- discards stale leases before writes;
- records one deduplicated unchanged external boundary and moves to the next PR or repository-owned task;
- does not wait after handing a gate-clean PR to central merge automation.

Queued, pending, skipped-required, neutral-required, absent, stale-head, predecessor-head, cancelled, and synthetic-merge-only evidence is not passing.

### Product continuation

The empty-queue mode resumes or creates one durable `agent-task` and develops one coherent buyer-visible slice.

Open PRs are not a blanket prohibition on all independent work. After executable PR repairs and shared blockers are exhausted, maintenance mode may create at most one additional draft product PR per invocation if a refreshed proof shows no overlap in files, schemas, migrations, generated artifacts, dependency ancestry, or writer ownership. Only one branch is actively mutated at a time, and extending an existing coherent PR is preferred.

If a PR appears during product mode, only conflicting writes stop. The loop switches to exact-head PR maintenance, then resumes or selects a demonstrably disjoint slice.

### Credential and command isolation

Before repository-owned gate code runs, the workflow installs root-owned `cwl-safe-exec`.

The wrapper:

- executes under `cwl-untrusted`;
- grants workspace access through the dedicated `cwl-workspace` group rather than the runner default group;
- refuses execution outside `GITHUB_WORKSPACE`;
- starts with a clean environment;
- removes model, GitHub, OIDC, and provider credentials;
- passes only `NVIDIA_NIM_API_KEY_CONFIGURED` to deterministic gate code;
- is verified as `root:root` mode `0755`.

Evidence files are stored under `.agent/evidence`; gate output is precreated as group-writable before unprivileged execution and appended to the protected GitHub output file by the workflow control plane.

OpenCode uses a deny-by-default shell permission map. Repository-controlled interpreters, tests, package managers, builds, and scripts must run through `cwl-safe-exec`. Repository and review material is untrusted data and cannot authorize commands or secret handling.

### Governance boundary

The local scheduler never approves, enables auto-merge, merges, tags, publishes, or releases. Organization-central required workflows remain authoritative for review, security, branch freshness, and merge.

## Scheduler recovery

If the deterministic gate fails because the NVIDIA key marker, repository identity, complete PR metadata, or durable task inventory is invalid, dispatch fails closed with a machine-readable reason. Malformed complete-queue metadata intentionally blocks mutation because selecting around an untrusted inventory could violate writer ownership. The next recurrence retries after live evidence is recollected; repository maintainers must repair the metadata or integration rather than bypassing validation.

A workflow file on a PR branch cannot schedule itself. Its cron is operational only after protected-branch merge.
