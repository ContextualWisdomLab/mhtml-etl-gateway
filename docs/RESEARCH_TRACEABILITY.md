# Standards and Research Traceability

| Decision | Authority | Product consequence |
|---|---|---|
| MHTML aggregate structure and Content-Location | RFC 2557 | parse MIME aggregate; never trust location as origin; protect file URIs |
| root `start`, first-direct-body default, and required type | RFC 2387 plus verified erratum 5578 | deterministic root; diagnose enterprise missing type; reject mismatch and nested substitution |
| opaque time-ordered external IDs | RFC 9562 | future service/database UUIDv7 contract |
| API description | OpenAPI 3.2.0 | future authenticated service contract baseline |
| PostgreSQL baseline | PostgreSQL 18.4 release notes | patched deployment baseline for future loader |
| secure development | NIST SP 800-218 SSDF 1.1 | design decisions, provenance, vulnerability, least privilege, and isolated build/test environments |
| application verification | OWASP ASVS 5.0.0 | future API/auth/session/validation acceptance criteria |
| SBOM | SPDX 3.0.1 | release inventory and vulnerability relationships |
| source/build provenance | SLSA 1.2 | signed release/source attestations |
| observability | OpenTelemetry 1.59.0 | privacy-safe traces, metrics, logs |
| information-security management | ISO/IEC 27001:2022/Amd 1:2024 | service-scope control evidence |
| service organization controls | AICPA 2017 TSC revised 2022 | security, availability, processing integrity, confidentiality, privacy evidence |
| Korean cloud assurance | KISA CSAP | service scope, assets, evaluation, vulnerability and penetration-test readiness |
| scheduled coding agent | OpenCode GitHub Action documentation | protected schedule, NVIDIA NIM authentication, private sessions, bounded repository write permissions |
| granular coding-agent tool control | OpenCode permissions documentation | default-deny shell patterns, explicit bounded Git/GitHub operations, `.env` read denial, and repository-code execution only through the secret-stripped wrapper |
| untrusted repository execution isolation | NIST SP 800-218 SSDF 1.1 and OpenCode permission controls | repository tests/builds run under a separate unprivileged identity with an empty environment rather than inheriting model, GitHub, OIDC, or provider credentials |

The reference list in `docs/doctoring/REFERENCES.md` uses APA 7th style and records the stable source for each decision.
