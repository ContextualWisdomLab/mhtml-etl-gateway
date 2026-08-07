# Operability

## Current library operation

The current slice is synchronous and local. It has no listening port, database credential, background thread, or network egress. Operators control resource budgets through `ParseLimits` and the CLI source-byte limit.

## Logging

Applications may log stable error/diagnostic codes, source hash, byte size, table dimensions, parser version, duration, and correlation ID. They must not log paths, Content-ID, raw Content-Location, header values, row values, decoded HTML, or exception chains containing source data.

## Metrics for future service

- intake count and bytes;
- parse success/failure by stable code;
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

Incidents are classified by source leakage, tenant-boundary failure, data corruption, execution/fetch boundary violation, unavailable ingestion, credential exposure, or supply-chain compromise. Containment can disable uploads or loading while preserving read-only audit and source custody.

## Capacity

Resource limits are per document and independent of deployment capacity. A future worker pool adds queue quotas, tenant concurrency, backpressure, and hard memory limits. Large input does not justify disabling parser budgets.

## Hourly development operation

The product-development workflow is not runtime processing. It runs hourly on the protected default branch, keeps sessions private, uses one durable task lease, and stops when a PR already exists. Central organization workflows process review and merge independently.
