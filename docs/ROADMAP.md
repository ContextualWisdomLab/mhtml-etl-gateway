# Roadmap

## M0 — Governance and deterministic inspection

Exit criteria:

- accepted PRD/TRD/architecture/ADR baseline;
- immutable source identity;
- bounded MIME/root/charset/table inspection;
- metadata-only default output and protected header opt-in;
- nonreflection and Content-Location hashing;
- realistic/hostile tests;
- 100% production line/branch/docstrings;
- exact-head CI and central governance;
- private hourly OpenCode product loop.

## M1 — Versioned schema governance

- table/header fingerprints;
- multiword `snake_case` normalization;
- conservative type evidence;
- leading-zero identifier protection;
- proposal JSON Schema;
- human/policy approval and immutable decision artifact;
- pg-erd-cloud visualization handoff.

## M2 — Transactional PostgreSQL loading

- `raw_import`, `staging_data`, `normalized_data`, and `audit_log` migrations;
- UUIDv7 IDs;
- streamed `COPY FROM STDIN`;
- rejection quarantine;
- row-level lineage;
- exact reconciliation and rollback;
- idempotent replay.

## M3 — Service plane

- authenticated asynchronous job API described in OpenAPI 3.2.0;
- encrypted object storage;
- tenant isolation and PostgreSQL RLS;
- readiness/liveness separation;
- retries, cancellation, dead-letter recovery;
- OpenTelemetry traces/metrics/logs.

## M4 — Enterprise governance

- SSO/SCIM ports;
- KMS and customer-managed-key option;
- retention, deletion, and legal hold;
- export approval;
- immutable audit export;
- CSAP/SOC 2/ISO 27001 control evidence;
- regional deployment/data-residency profiles.

## M5 — Ecosystem connectors

- naruon notifications and governed handoff;
- pg-erd-cloud schema/lineage visualization;
- pg-llm-batch post-ingestion enrichment;
- contextual-orchestrator policy/review adapter;
- generic webhook, object-store, and database ports.

## M6 — Release hardening

- SPDX 3.0.1 SBOM;
- SLSA 1.2 source/build provenance;
- signed reproducible artifacts;
- performance and capacity evidence;
- support/upgrade/rollback contract;
- versioned migrations and compatibility policy.
