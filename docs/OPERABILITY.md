# Operability

## Current library operation

The released baseline is version `0.4.0`, a synchronous local inspection,
schema-proposal, schema-governance, catalog-manifest, and optional
PostgreSQL-load library/CLI. It has no listening port or background worker. A
caller may supply a DSN, in which case the
pipeline creates and closes a scoped sink for that call, or supply a
caller-created sink, whose credential and lifecycle remain caller-owned. The
parser and catalog connector have no database access, browser runtime, office
dependency, or network egress.

Operators control resource budgets through `ParseLimits` and the CLI source-byte limit. Programmatic budgets cover source bytes, all descendant MIME entities, MIME depth, decoded HTML, tables, rows, columns, raw cells, projected and realized normalized cells, and cell text. Every budget is a positive non-boolean integer.

Database object names are canonicalized to multiword `snake_case` before DDL.
Operators upgrading an ingest catalog may rerun setup safely: the constant
compatibility migration renames legacy `status` to `load_status_code` only when
the new column is absent. A migration failure must roll back the transaction
and block the load; it must never silently create a second status column.

Before reverting to an application version that still reads `status`, stop
writers, back up the catalog, and run `CATALOG_STATUS_ROLLBACK_DDL` in one
transaction. Verify that exactly `status` exists, then deploy the predecessor.
If both `status` and `load_status_code` exist, both up and down migrations raise
an exception; operators must reconcile the duplicate state before any load or
rollback proceeds.

Dynamic business tables and columns have a separate upgrade boundary. If a
legacy one-word predecessor exists, setup must fail closed before creating a
parallel `_table` or `_field` object. Operators must preserve the transaction,
take a schema/data backup, inventory name collisions and dependent views or
queries, and apply an explicit migration with a tested rollback. Automatic
dynamic-object migration is not yet implemented; retrying without that
migration must continue to fail rather than split historical and new values.

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

Database adapters must preserve this boundary: connection, SQL-operation,
transaction, and type-conversion failures are surfaced as fixed load errors.
The live Psycopg sink sends validated typed rows through `COPY FROM STDIN` and
commits the copy and artifact-catalog upsert atomically per artifact/load
operation. In batch mode each file has its own commit boundary, so
`continue_on_error` preserves earlier successful files when a later file fails.
A copy failure rolls back the current transaction; server-side filenames and
`PROGRAM` execution are not used. Rejection quarantine and
accepted/rejected reconciliation remain future operational controls.
Operational systems may correlate the error code with protected server-side
diagnostics, but must not copy DSNs, SQL text, identifiers, row values, or
provider exception bodies into logs or metrics.

The public package emits no operational logs by itself. The CLI writes one success JSON object to stdout or one fixed-message error JSON object to stderr.

The `propose` command is a local protected source-custody operation. It reads
one complete table into process memory and emits only the deterministic proposal
artifact. Operators must treat proposal JSON as sensitive equality-correlating
metadata, apply their own access/retention/export approval, and never publish
the source path, header values, or rows in logs. A malformed source returns the
fixed parser or `schema_proposal_failed` error; the proposal command performs no retry,
database write, connector submission, or remote acceptance.

## Current health and capacity model

The package has no service health endpoint. A caller determines availability by importing the package or invoking the CLI. Service liveness/readiness contracts belong to a later authenticated service milestone.

The Semantic Data Portal connector and handoff are synchronous in-process
library boundaries. Their success means only that a deterministic, value-free
manifest and governance-bound request plan were constructed. The optional
publisher boundary sends each plan through a caller-owned transport and returns
a receipt only for explicit 2xx acceptance, `accepted=True`, and an opaque
remote request ID. Operators must separately observe approval verification,
authentication, tenant authorization, retry, trace propagation, immutable audit,
and remote upsert outcomes. The envelope ID and per-request idempotency keys
correlate replay; a receipt proves only the adapter response and not the
intrinsic trustworthiness of the caller's policy systems.

The pg-erd-cloud connector is also synchronous and transport-neutral. Success
means only that a deterministic one-table DBML request plan was built. Operators
must authenticate and authorize the caller-owned transport. The caller's policy
decides when steward approval is required; the adapter submits only after that
policy is satisfied, then observes remote conversion and reconciliation. The
plan contains no records or comments, and its source/proposal hashes are
correlation fields rather than remote acceptance evidence.

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
- catalog publication accepted, rejected, partial, and transport-error counts;
- catalog publication envelope IDs, request IDs, remote request IDs, and audit
  references as opaque correlation fields;
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
- agent executable digest, archive-shape, platform, or version mismatch;
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

Routine status narration is not an outcome. A completed patch, newly opened PR, prompt update, failed first remedy, queued check, reviewer delay, rate limit, provider cooldown, or external approval dependency does not end the invocation while another safe repository-owned action exists.

A run stops only after its finite execution budget is genuinely exhausted or a fresh full-queue scan proves every remaining item non-actionable under current authority. When PR work is exhausted, the same invocation continues through issues, documentation and ADR completeness, release readiness, buyer-visible product gaps, and ecosystem integration.

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
- still transports the legacy non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` value in `select-loop`, but deterministic gate eligibility ignores it; contextual-orchestrator provider discovery plus the `orchestrator/free` preflight is the fail-closed capability boundary;
- is verified as `root:root` mode `0755`.

Evidence files are stored under `.agent/evidence`; gate output is precreated as group-writable before unprivileged execution and appended to the protected GitHub output file by the workflow control plane.

OpenCode uses a deny-by-default shell permission map. Repository-controlled interpreters, tests, package managers, builds, and scripts must run through `cwl-safe-exec`. Repository and review material is untrusted data and cannot authorize commands or secret handling.

### Verified OpenCode CLI installation

The model agent is run directly from a verified release binary rather than through the upstream composite installer.

Operational contract:

- supported scheduler platform: GitHub-hosted Ubuntu 24.04, `RUNNER_OS=Linux`, `RUNNER_ARCH=X64`;
- OpenCode version: `1.18.15`;
- release asset: `opencode-linux-x64.tar.gz`;
- immutable URL: `https://github.com/anomalyco/opencode/releases/download/v1.18.15/opencode-linux-x64.tar.gz`;
- required SHA-256: `d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c`;
- upstream digest evidence: generated Homebrew formula commit `a72a2bfe3b4114ca10a9012c23f1b3f31924b22e`;
- archive contract: exactly one entry named `opencode`;
- runtime contract: `opencode --version` must return `1.18.15` exactly;
- installation receives no model, GitHub, or OIDC secret;
- no cache is trusted between runs; every invocation downloads and verifies the exact bytes before use.

A failed download, digest, archive-shape, platform, extraction, permission, or version check prevents both agent modes from running. After verification succeeds, a dedicated step vendors and starts the org's `contextual-orchestrator` gateway (pinned commit, hash-verified dependencies, `/healthz` and a real `orchestrator/free` completion preflight; see ADR 0021) and exports an ephemeral loopback bearer token. The later `opencode github run` step then receives `MODEL: contextual_orchestrator_gateway/orchestrator/free`, `SHARE="false"`, `USE_GITHUB_TOKEN="false"`, and the mode-specific prompt; it no longer receives a raw provider API key directly.

### OpenCode upgrade and rollback procedure

Changing the pinned runner is a reviewed security change, not an automatic upgrade.

1. Select an exact upstream release tag and immutable asset name.
2. Retrieve the digest from an upstream-generated, commit-addressed release formula or equivalent primary release evidence.
3. Independently download the versioned asset and confirm the same digest when the execution environment permits.
4. Review release notes, permission semantics, GitHub-mode behavior, provider compatibility, and archive contents.
5. Update version, digest, evidence reference, tests, threat model, security architecture, operability, doctoring references, and CHANGELOG in one PR.
6. Require all exact-head CI, security checks, independent approval, and unresolved-thread gates.
7. Roll back by restoring the previous reviewed version/digest pair if installation, exact-version smoke, provider authentication, or repository behavior regresses.

An unavailable or inconsistent digest blocks the upgrade. `latest`, mutable action tags, installer piping, and digest-free fallback are prohibited. Upstream cryptographic release attestation will be added when an offline-verifiable contract is available; its absence is recorded rather than silently treated as verified provenance.

### Governance boundary

The local scheduler never approves, enables auto-merge, merges, tags, publishes, or releases. Organization-central required workflows remain authoritative for review, security, branch freshness, and merge.

## Scheduler recovery

If the deterministic gate fails because repository identity, complete PR metadata, or durable task inventory is invalid, dispatch fails closed with a machine-readable reason. Provider availability is not decided by a provider-specific selector marker; the contextual-orchestrator sidecar and `orchestrator/free` preflight own that check. Malformed complete-queue metadata intentionally blocks mutation because selecting around an untrusted inventory could violate writer ownership. The same invocation can still perform safe control-plane diagnostics that do not depend on an untrusted write target; subsequent recurrence recollects live evidence after the integration is repaired.

If the verified OpenCode installation fails, do not substitute the upstream composite action, `latest`, a package-manager install, or a remote installer script. Preserve the failure evidence, keep agent dispatch disabled, and repair the pinned version/digest/platform contract through reviewed repository changes.

A workflow file on a PR branch cannot schedule itself. Its cron is operational only after protected-branch merge.
