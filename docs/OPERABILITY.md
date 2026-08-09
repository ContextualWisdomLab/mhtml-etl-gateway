# Operability

## Current library operation

The current slice is synchronous and local. It has no listening port, database credential, background thread, or network egress. Operators control resource budgets through `ParseLimits` and the CLI source-byte limit. Programmatic budgets include total source bytes, total descendant MIME entities, MIME nesting depth, decoded HTML, tables, rows, columns, normalized cells, and cell text.

## Logging

Applications may log stable error/diagnostic codes, source hash, byte size, table dimensions, parser version, duration, and correlation ID. They must not log paths, Content-ID, raw Content-Location, header values, row values, decoded HTML, MIME boundary values, or exception chains containing source data.

## Metrics for future service

- intake count and bytes;
- parse success/failure by stable code;
- MIME entity count and nesting-depth rejection count;
- document/table dimensions by bounded histogram;
- compatibility diagnostic count;
- duration and peak memory;
- schema-review queue depth;
- load/reconciliation result;
- retry, rollback, and dead-letter counts;
- tenant-scoped SLO without raw labels.

OpenTelemetry 1.59.0 is the observability baseline. Trace attributes use opaque IDs and hashes.

## Service SLO candidates

- accepted-job durability: 99.99%;
- parser availability excluding rejected unsafe input: 99.9%;
- reconciliation-complete load success for valid approved inputs: 99.9%;
- unauthorized cross-tenant disclosure: 0;
- lost immutable source after acknowledgement: 0;
- unbalanced load marked complete: 0.

## Backup and disaster recovery

Raw source objects, approved schema artifacts, audit events, and PostgreSQL state require encrypted, versioned backup. Restoration tests prove lineage and reconciliation integrity. Legal-hold and deletion semantics must be explicit for both payload and audit evidence.

## Incident response

Incidents are classified by source leakage, tenant-boundary failure, data corruption, execution/fetch boundary violation, unavailable ingestion, parser resource exhaustion, credential exposure, or supply-chain compromise. Containment can disable uploads or loading while preserving read-only audit and source custody.

## Capacity

Resource limits are per document and independent of deployment capacity. A future worker pool adds queue quotas, tenant concurrency, backpressure, and hard memory limits. Large input does not justify disabling parser budgets. Operators may lower `max_mime_depth` and total MIME entity count for constrained deployments; every budget remains a positive value.

## Hourly autonomous-development operation

The scheduled workflow is not runtime processing. It runs hourly from the protected default branch, uses private NVIDIA NIM sessions, and serializes runs with a repository-wide non-cancelling concurrency group.

When pull requests are open, the deterministic gate validates the full queue, selects the lowest-numbered PR as the initial cursor, and passes an exact head/base lease to PR-maintenance mode. The agent performs RCA, proves remediation feasibility, fixes repository-owned defects on the existing branch, and may rerun only exact-head failed or cancelled Actions jobs that are demonstrably transient. Fork heads are read-only. Queued, pending, skipped-required, absent, stale-head, and cancelled evidence is never treated as passing.

If the initial PR has no executable repository-owned action, the agent records one deduplicated boundary and advances to the next open PR while meaningful execution capacity remains. It does not repeatedly re-prove an unchanged approval, policy, provider, or permission blocker. Branch writes remain serialized: at most one PR branch is actively mutated at a time, and every transition to another PR starts with a fresh exact-head/base lease.

The job token includes read-only code-scanning access so the prompt's stated security-evidence inspection is operationally feasible. Pull-request source, comments, issues, reviews, logs, and artifacts remain untrusted data rather than instructions. The agent derives commands independently and may not print or transmit environment variables or secret values.

When the PR queue is empty, the workflow resumes or creates one durable `agent-task` issue and develops one bounded buyer-visible gap. A newly appeared PR cancels product writes through live reconciliation. The workflow never approves, merges, enables auto-merge, tags, publishes, or releases; central organization workflows remain authoritative for those actions.

The scheduler file must be present on the default branch before GitHub executes its cron. A PR containing scheduler changes is therefore verified manually and by PR CI, but cannot use the new schedule to repair itself before merge.
