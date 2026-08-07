# Threat Model

## Assets

- customer MHTML bytes and derived rows;
- PII and confidential business fields;
- source hashes, schema approvals, and lineage;
- PostgreSQL credentials and tenant keys;
- scheduled-agent credentials and repository write authority;
- release artifacts, SBOM, and provenance.

## Trust boundaries

1. source file to parser;
2. parser memory to inspection artifact;
3. inspection to schema governance;
4. approved schema to future loader;
5. loader to PostgreSQL;
6. GitHub schedule to OpenCode agent;
7. product repository to central organization governance.

## Principal threats and mitigations

| Threat | Impact | Mitigation |
|---|---|---|
| deceptive `start` or duplicate Content-ID | wrong source selected | exact cross-media uniqueness and HTML check |
| later HTML substituted for non-HTML default root | semantic substitution | RFC first-body rule |
| duplicate critical header/parameter | parser differential | raw cardinality validation before selection |
| malformed structured Content-Type | undefined root semantics | header defect rejection |
| missing RFC type in enterprise export | availability loss or silent divergence | diagnosed compatibility lane plus direct root validation |
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
| scheduled-agent overlap | conflicting PRs | durable issue lease, open-PR gate, concurrency |
| compromised dependency/action | supply-chain compromise | dependency minimization, full-SHA pins, SBOM/provenance |

## Residual risks

- The Python standard-library email parser remains a complex upstream dependency and must be tracked across supported Python patch versions.
- A metadata hash may still support equality correlation; access and retention controls apply to hashes.
- Header-value opt-in can expose protected values if an operator redirects output to an unsafe location.
- Deterministic structural inspection does not prove business-semantic correctness; reviewed mappings and reconciliation remain required.
