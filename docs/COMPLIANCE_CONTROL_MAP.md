# Compliance Control Map

This map is engineering evidence, not certification or legal advice. An assessor evaluates the deployed service boundary, organization, people, procedures, and operating evidence.

| Product control | ISO/IEC 27001 readiness | SOC 2 Trust Services Criteria | CSAP readiness | Evidence |
|---|---|---|---|---|
| immutable source hash and lineage | asset/integrity/change evidence | security, processing integrity | asset/data integrity | report, lineage artifact, tests |
| tenant isolation and future RLS | access control | security, confidentiality, privacy | tenant separation | policy, integration tests, audit |
| encryption and scoped keys | cryptographic controls | confidentiality, security | data protection | KMS config and rotation evidence |
| metadata-only logs/reports | data minimization | confidentiality, privacy | personal-data protection | nonreflection tests |
| approved schema artifact | change management | processing integrity | change control | ADR, approval record, hash |
| multiword database object naming | secure configuration/change control | security, processing integrity | schema integrity | ADR-0016, identifier tests, DDL/migration evidence |
| actor/tenant/approval-bound catalog handoff | access/change accountability | security, confidentiality, processing integrity | access/audit | envelope ID and request keys are correlation/deduplication evidence only; caller-owned actor authentication, tenant authorization, approval verification, remote acceptance, and immutable audit records are recorded separately |
| bounded catalog publication receipt | processing integrity and audit evidence | security, processing integrity, confidentiality | access/audit/integrity | caller-owned evidence gates plus explicit 2xx/accepted/opaque remote ID; safe receipt and accepted-prefix error exclude request/provider bodies |
| reconciliation and rollback | operations/integrity | availability, processing integrity | continuity/integrity | loader tests and run evidence |
| full-SHA actions, SBOM, provenance | supplier/software security | security | supply-chain controls | CI, SPDX, SLSA attestation |
| vulnerability and private reporting | incident/vulnerability management | security | vulnerability response | SECURITY.md, advisories, SLA |
| backups and restore tests | continuity | availability | backup/recovery | restore evidence |
| audit and export approval | logging/accountability | security, confidentiality, privacy | audit/access | immutable events and approvals |

## Framework baselines

- ISO/IEC 27001:2022 with Amendment 1:2024;
- AICPA 2017 Trust Services Criteria with revised points of focus (2022);
- KISA Cloud Security Assurance Program requirements applicable to the selected service type and grade;
- NIST SSDF 1.1 as the current final publication, while SSDF 1.2 remains a public draft as of this baseline;
- OWASP ASVS 5.0.0 for future network/application surfaces.
