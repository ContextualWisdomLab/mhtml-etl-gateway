# Standards and Research Traceability

| Decision | Authority | Product consequence |
|---|---|---|
| semantic catalog interoperability | World Wide Web Consortium, DCAT 3 | model the future catalog publication boundary around dataset identity, versioning, checksum, and discoverability without claiming a complete JSON-LD publisher in the connector slice |
| graph request validation and governed handoff | ContextualWisdomLab. (2026). *Semantic Data Portal graph node and edge request contracts* [Source code, commit e48aa13c4af7a4875d4b53e6a60b50405c265a2f; `src/sdp/api.py`, `src/sdp/graph_models.py`]. GitHub. https://github.com/ContextualWisdomLab/semantic-data-portal/tree/e48aa13c4af7a4875d4b53e6a60b50405c265a2f/src/sdp | emit request-compatible dataset/column nodes and edges, bind an explicit actor/tenant/approval context, scope request idempotency by tenant and approval, and keep credential/transport authority outside this library |
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
| privileged OpenCode executable identity | OpenCode v1.18.15 publisher source and commit-addressed generated Homebrew formula | remove the mutable composite installer; pin the Linux x64 release URL, SHA-256, archive shape, and exact runtime version before credential exposure |
| coding-agent release rollback | NIST SP 800-218 SSDF 1.1 and ADR-0011 | version/digest changes require reviewed evidence and fail closed; rollback restores the prior accepted pair rather than using `latest` or an unverified installer |

The reference list in `docs/doctoring/REFERENCES.md` uses APA 7th style and records the stable source for each decision.
