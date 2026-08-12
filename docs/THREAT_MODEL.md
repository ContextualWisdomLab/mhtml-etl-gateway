# Threat Model

## Assets

- customer MHTML bytes and derived rows;
- PII and confidential business fields;
- source hashes, protected schema evidence, approvals, and lineage;
- scoped PostgreSQL credentials and future tenant keys;
- scheduled-agent model credentials and repository write authority;
- verified OpenCode executable identity and digest evidence;
- current-head review, check, code-scanning, and branch-policy evidence;
- release artifacts, SBOM, and provenance.

## Trust boundaries

1. source file to MIME parser;
2. decoded root HTML to table extractor;
3. parser memory to public inspection artifact;
4. inspection evidence to protected schema governance;
5. approved or caller-authorized schema to the current loader;
6. current loader to PostgreSQL;
7. GitHub schedule to versioned OpenCode archive download and digest verification;
8. verified OpenCode executable and model credential to privileged agent control plane;
9. untrusted repository/review/log/artifact material to privileged agent reasoning;
10. privileged agent process to secret-stripped repository-code execution;
11. product repository to central organization governance.
12. value-free catalog manifest to caller-owned Semantic Data Portal transport.
13. governance-bound catalog handoff envelope to caller-owned authenticated publisher.
14. caller-owned catalog publisher to remote response and acceptance evidence.
15. value-free schema proposal to caller-owned pg-erd-cloud visualization transport.
16. local protected MHTML table extraction to the value-free proposal serializer.

## Principal threats and mitigations

| Threat | Impact | Mitigation |
|---|---|---|
| deceptive `start` or duplicate Content-ID | wrong source selected | exact cross-media uniqueness before media-type validation |
| later or nested HTML substituted for non-HTML direct root | semantic substitution | RFC first-direct-body rule |
| duplicate critical header or parameter | parser differential | raw cardinality validation before selection |
| malformed structured Content-Type | undefined root semantics | header defect rejection |
| missing RFC type in enterprise export | availability loss or silent divergence | diagnosed compatibility lane plus direct root validation |
| extreme multipart nesting | recursion exhaustion or denial of service | fixed recursion conversion, `max_mime_depth`, iterative traversal |
| many multipart containers with few leaves | entity-count bypass | `max_mime_parts` counts every descendant body entity |
| oversized decoded text | memory/CPU exhaustion before extraction | `max_html_chars` immediately after strict decode |
| duplicate span attributes | parser-dependent geometry | case-insensitive duplicate rejection |
| rowspan/colspan expansion bomb | logical-cell allocation exhaustion | raw-cell bound and pre-allocation projected-cell bound |
| mismatched inert closing tag | hidden text enters extraction | exact suppression stack; unmatched close cannot pop another boundary |
| iframe/object embedded descendants | hidden or remote-resource text enters cells | inert container suppression |
| void embed treated as container | following legitimate text disappears | HTML-void handling with attribute/payload ignorance |
| script/template/resource payload | code execution or data exfiltration | non-rendering parser, suppression, no egress |
| file URI in Content-Location | internal path disclosure | raw value and scheme omitted; exact value represented only by SHA-256 |
| source-controlled media metadata in public JSON | classification/path leakage | public report omits media type, charset, transfer encoding, and location scheme |
| payload value reflected in errors/logs | PII or confidential-data breach | stable codes and fixed approved-safe messages |
| charset confusion | data corruption | registered charset, BOM, then strict UTF-8 |
| nonstandard transfer encoding | silent corruption | identity compatibility diagnostic without relaxing other controls |
| public header-value switch | unaudited data disclosure | no public API or CLI header path |
| local proposal output discloses headers or cells | PII or confidential-data breach | keep source headers/rows in process memory, serialize only the existing value-free proposal, and test protected-value absence in CLI and Python wrapper output |
| schema injection | arbitrary DDL | future versioned approved artifact and identifier allowlist |
| duplicate import | duplicate business records | future source hash plus tenant-scoped idempotency |
| partial PostgreSQL load | inconsistent target | atomic transaction, streamed `COPY FROM STDIN`, rollback, and opaque lineage; future staging/reconciliation controls |
| cross-tenant access | confidentiality breach | future tenant keys, RLS, scoped service identity, and audit |
| public OpenCode session | source leakage | direct `SHARE: "false"` plus repository `share: disabled` tests |
| mutable nested OpenCode action | privileged code changes without repository review | upstream composite removed; direct verified binary execution |
| latest-release lookup | unreviewed version enters privileged boundary | exact `1.18.15` release URL only |
| remote installer script compromise | arbitrary code before agent startup | no installer script; direct archive download only |
| release archive substitution | credential theft or repository takeover | reviewed SHA-256 checked strictly before extraction |
| archive path or metadata abuse | overwrite or privilege confusion | exact single-entry archive shape and no preserved ownership/permissions |
| wrong platform or binary version | incompatible or unexpected executable | Linux x64 assertions and exact `opencode --version` gate |
| credentials exposed during installation | compromised download path gains secrets | install step binds no model, GitHub, or OIDC secret |
| PR/comment/log prompt injection | secret disclosure, scope expansion, unsafe command | untrusted-data classification, trusted prompt precedence, copied-command prohibition |
| repository code inherits model/GitHub/OIDC credentials | credential theft or unauthorized API use | root-owned clean-environment wrapper under separate UID/group |
| wrapper output owned only by privileged runner | gate failure and false autonomy | precreate evidence/output files group-writable for `cwl-workspace` |
| untrusted user inherits runner default group | access beyond intended workspace | dedicated `cwl-workspace` group only |
| raw GitHub API mutation bypass | unintended review/merge/protection change | deny arbitrary shell and mutating raw API forms; central merge boundary |
| stale or fork PR mutation | lost work or unauthorized branch write | exact-head lease, live refetch, same-repository write check |
| scheduled-agent overlap | conflicting PRs | repository concurrency, serialized branch mutation, durable task lease |
| low-numbered externally blocked PR | starvation of later work | deduplicated boundary plus work-conserving queue progression |
| gate-clean PR waits for central merge | idle execution capacity | merge handoff then next executable item |
| unrelated product work overlaps active PR | merge conflict or invalid evidence | refreshed non-overlap proof and one-extra-draft limit |
| repeated proof or rerun of unchanged blocker | Actions cost and comment noise | one evidence pass, bounded retry, then next item |
| claimed code-scanning RCA without token scope | incomplete or fabricated conclusion | `security-events: read` workflow contract |
| malformed or hidden `.yaml` workflow evades policy scanner | mutable action or credential drift | recursive `.yml` and `.yaml` validation |
| false remediation activity | no blocker change despite cost | mandatory permission/API/effect feasibility proof |
| compromised dependency/action | supply-chain compromise | dependency minimization, hash locks, full-SHA pins, verified agent binary, future SBOM/provenance |
| catalog connector receives or emits protected values | semantic-catalog disclosure | accept only value-free `SchemaProposal` output, serialize hashes/aggregates/review reasons only, test raw-value absence, and leave transport/approval outside the library |
| anonymous or cross-tenant catalog replay | unauthorized graph write or confused-deputy disclosure | require explicit actor, bounded tenant/approval references, tenant- and approval-scoped deterministic envelope/request IDs, reject surrounding whitespace, and require caller-owned actor authentication, tenant authorization, approval verification, remote acceptance, and immutable audit evidence |
| one-word or attacker-shaped database identifier | inconsistent schema, SQL injection, or migration drift | canonicalize generated names to multiword `snake_case`, reserve suffixes within 63 bytes, reject unsafe direct identifiers before DDL, and run only constant catalog migration SQL |
| numeric input exceeds PostgreSQL BIGINT range | insert failure or unsafe type coercion | bound integer inference to signed BIGINT and infer `NUMERIC` for larger values; live schema evolution promotes incompatible existing columns to `TEXT` before writes |
| arbitrary caller type reaches generated DDL | SQL injection or invalid schema mutation | enforce a fixed PostgreSQL type allow-list inside `TableSchema.create_ddl` before any SQL is sent |
| database/identifier exception reflects secrets or schema details | DSN, PII, or database reconnaissance disclosure | convert connection, operation, load, and identifier failures to fixed messages; CLI also emits only approved safe summaries |
| provider error or response body reflected by publisher | PII, credentials, or provider-internal disclosure | validate only status/acceptance/opaque remote ID, expose fixed publisher codes and request index, and keep provider bodies in the caller-owned adapter |
| DBML visualization receives raw values or executable metadata | diagram disclosure or parser-side injection | derive DBML only from value-free proposals, allow-list types and identifiers, emit no comments/notes/defaults/records/relationships, and keep transport/authentication caller-owned |
| false remote acceptance | silent catalog divergence | require explicit 2xx success, `accepted=True`, and opaque remote request ID before each receipt entry is recorded |
| partial remote outcome | incomplete graph or unsafe replay | report only the accepted prefix count, preserve idempotency keys, and require caller-owned reconciliation before retry or completion |
| publisher acquires hidden authority | confused deputy or standalone behavior change | use a transport protocol with no credentials, network, retry, persistence, auth, or approval implementation in the gateway |

## Residual risks

- The Python standard-library email parser remains a complex upstream dependency. Source, count, and depth controls reduce impact, but parsing can consume CPU and memory before upstream recursion exhaustion is raised. Supported Python patch versions require continued fuzzing and regression tracking.
- Default resource limits require deployment-specific capacity evidence. Operators may lower them but must not disable positive bounds.
- The privileged OpenCode process still needs model access and repository control capabilities. The exact archive digest and version are now verified before credentials are bound, but the upstream project does not currently provide an offline-verifiable release attestation contract for this asset. The reviewed upstream generated formula and repository-pinned digest are therefore the current provenance evidence, not a claim of cryptographic builder identity.
- The GitHub-hosted runner image, operating system tools, network path, and GitHub OIDC exchange remain external trust dependencies. Runner hardening, strict archive digest verification, minimal permissions, and central governance reduce but do not eliminate those dependencies.
- `security-events: read` does not grant every Dependabot or organization-governance API. Unavailable evidence remains an explicit boundary and cannot be inferred as passing.
- Current OpenCode command patterns depend on the permission engine's documented last-match semantics. Configuration changes require contract tests and upstream-version review.
- A metadata hash permits equality correlation; access and retention controls apply to hashes.
- Deterministic structural inspection does not prove business-semantic correctness. Protected mapping review and load reconciliation remain required future controls.
- The current parser is in-memory and not yet a streaming service; very large but within-budget sources still require capacity benchmarks before production deployment.
