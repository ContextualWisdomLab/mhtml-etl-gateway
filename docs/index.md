# MHTML ETL Gateway

MHTML ETL Gateway is a deterministic, privacy-preserving ingestion boundary for enterprise MHTML exports. It inspects untrusted MIME/HTML without rendering active content, proposes governed PostgreSQL schemas, and loads rows with opaque lineage.

## Start here

- [Repository README](../README.md) — capabilities, installation, CLI usage, safety, and release-facing status.
- [Product requirements](PRD.md) — product scope and requirements.
- [Technical requirements](TRD.md) — runtime and implementation contracts.
- [Architecture](ARCHITECTURE.md) — bounded components and ecosystem seams.
- [Threat model](THREAT_MODEL.md) — trust boundaries and abuse cases.
- [Operations](OPERABILITY.md) — operating and recovery guidance.
- [Architecture decisions](adr/README.md) — reviewed design decisions.

## Product boundary

The gateway owns safe ingestion of MHTML/HTML tabular exports through deterministic parsing, schema governance, PostgreSQL loading, and value-free handoff contracts. Semantic catalog publication, diagram visualization, broader orchestration, and external network authority remain caller-owned integrations.

## Safety posture

MHTML is treated as untrusted input. The product does not execute scripts, render browsers, resolve XML entities, fetch external resources, or expose source values and local operator paths through public reports.

## Verification

Repository quality, security, static-analysis, coverage, and package checks provide evidence for the exact reviewed revision. This documentation does not claim certification or a published release beyond repository evidence.
