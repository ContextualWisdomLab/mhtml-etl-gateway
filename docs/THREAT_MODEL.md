# Threat Model

## Assets

- customer MHTML bytes and derived rows;
- PII and confidential business fields;
- source hashes, schema approvals, and lineage;
- PostgreSQL credentials and tenant keys;
- scheduled-agent model credentials and repository write authority;
- current-head review, check, code-scanning, and branch-policy evidence;
- release artifacts, SBOM, and provenance.

## Trust boundaries

1. source file to parser;
2. parser memory to inspection artifact;
3. inspection to schema governance;
4. approved schema to future loader;
5. loader to PostgreSQL;
6. GitHub schedule and model credential to OpenCode agent;
7. untrusted PR/review/log/artifact material to privileged agent reasoning;
8. product repository to central organization governance.

## Principal threats and mitigations

| Threat | Impact | Mitigation |
|---|---|---|
| deceptive `start` or duplicate Content-ID | wrong source selected | exact cross-media uniqueness before media-type validation |
| later or nested HTML substituted for non-HTML direct root | semantic substitution | RFC first-direct-body rule |
| duplicate critical header/parameter | parser differential | raw cardinality validation before selection |
| malformed structured Content-Type | undefined root semantics | header defect rejection |
| missing RFC type in enterprise export | availability loss or silent divergence | diagnosed compatibility lane plus direct root validation |
| extreme multipart nesting | recursion exhaustion or denial of service | stable recursion conversion, `max_mime_depth`, iterative traversal |
| many multipart containers with few leaves | leaf-count budget bypass | `max_mime_parts` counts all descendant body entities |
| mismatched suppressed closing tag | hidden active/template text enters extracted values | exact suppression stack; unmatched close cannot pop outer boundary |
| script/template/resource payload | code execution or data exfiltration | non-rendering parser, suppression, no egress |
| file URI in Content-Location | internal path disclosure | scheme plus SHA-256 only |
| payload value reflected in errors/logs | PII/confidentiality breach | fixed messages and metadata-only default |
| span or size expansion | CPU/memory exhaustion | independent and document-wide budgets |
| charset confusion | data corruption | registered charset/BOM/strict UTF-8 order |
| nonstandard transfer encoding | corrupt decode | identity compatibility diagnostic; no silent conformance |
| schema injection | arbitrary DDL | versioned approved artifact and identifier allowlist |
| duplicate import | duplicate business records | source hash plus tenant-scoped idempotency |
| partial PostgreSQL load | inconsistent target | transaction, staging, reconciliation, rollback |
| cross-tenant access | confidentiality breach | tenant keys, RLS, scoped service identity, audit |
| public OpenCode session | source leakage | `share: false` contract test |
| PR/comment/log prompt injection | secret disclosure, scope expansion, unsafe commands | all repository/review material classified as untrusted data; trusted prompt wins; copied commands prohibited |
| model credential reflected through shell, commit, comment, or log | NVIDIA key compromise | explicit secret nonreflection prohibition; no untrusted instruction can authorize environment access |
| stale or fork PR mutation | lost work or unauthorized branch write | exact-head lease, live refetch, same-repository write check |
| scheduled-agent overlap | conflicting PRs | repository concurrency, serialized branch mutation, durable issue lease |
| low-numbered externally blocked PR | starvation of actionable later PRs | deduplicated boundary plus work-conserving progression through the open queue |
| repeated proof or rerun of unchanged blocker | Actions cost, comment noise, no progress | one evidence pass, bounded retry, then next executable item |
| claimed code-scanning RCA without usable token scope | incomplete or fabricated security conclusion | job-level `security-events: read` contract and workflow test |
| false remediation activity | blocker remains while cost and noise increase | mandatory RCA plus permission/API/effect feasibility proof |
| compromised dependency/action | supply-chain compromise | dependency minimization, hash lock, full-SHA pins, SBOM/provenance |

## Residual risks

- The Python standard-library email parser remains a complex upstream dependency. Extreme input is converted to a stable error, but parsing may consume bounded CPU and memory before upstream recursion exhaustion is raised; supported Python patch versions must remain tracked and fuzzed.
- Source-byte, entity-count, and depth defaults require deployment-specific capacity validation; operators may lower them but must not disable positive bounds.
- Prompt instructions reduce but do not cryptographically prevent a model/tool implementation from reading its inherited process environment. Production activation therefore also depends on private sessions, scoped repository permissions, exact-head leases, audit evidence, runner hardening, and future secret-broker isolation.
- `security-events: read` enables code-scanning inspection but does not automatically grant every Dependabot or organization-governance API permission; the agent must prove each requested API is available and treat unavailable evidence as an explicit boundary.
- A metadata hash may still support equality correlation; access and retention controls apply to hashes.
- Header-value opt-in can expose protected values if an operator redirects output to an unsafe location.
- Deterministic structural inspection does not prove business-semantic correctness; reviewed mappings and reconciliation remain required.
