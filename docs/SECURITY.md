# Security Architecture

## Threat posture

MHTML files are attacker-controlled compound documents. They can carry active HTML, deceptive MIME roots, duplicate identifiers, malformed encodings, oversized or deeply nested structures, internal file locations, and sensitive customer data. The parser is therefore a data-only trust boundary.

The scheduled coding agent is a separate privileged control-plane risk. Repository source, comments, issues, reviews, logs, and artifacts can contain prompt-injection content, while the model process has repository write authority. Repository-controlled code must not inherit its credentials, and the executable that receives those credentials must be identified and verified before execution.

## Implemented parser controls

### No active execution

The production path has no browser, JavaScript, CSS renderer, office runtime, XML external-entity resolver, database connection, or resource fetcher.

`script`, `style`, `noscript`, `template`, `iframe`, and `object` descendants are suppressed with an exact nesting stack. A mismatched closing tag cannot pop a different outer inert boundary. The HTML-void `embed` element and its attributes are ignored without treating later sibling text as descendants.

### MIME ambiguity controls

- parser defects fail closed;
- duplicate critical singleton headers fail closed;
- duplicate `boundary`, `start`, and `type` parameters fail closed from raw header evidence;
- duplicate normalized Content-ID values fail closed across all descendant body entities;
- explicit start identifiers are classified for zero/one/many cardinality before media-type validation;
- no-start root is the first direct body part, never a later or nested HTML leaf;
- a selected root must be non-multipart `text/html`;
- declared type must match the selected root;
- missing type is a visible compatibility diagnostic, not silent conformance.

### Resource controls

The gateway enforces independent positive budgets for:

- source bytes before parsing;
- total MIME body entities, including multipart containers;
- MIME nesting depth;
- decoded HTML characters immediately after strict decoding;
- table count and rows per table;
- columns per table;
- raw source-cell construction before the next `_RawCell` allocation;
- projected normalized cells before span expansion allocation;
- realized normalized cells and projection/realization agreement;
- source cell text.

The standard-library email parser can recurse while constructing deeply nested input. Recursion exhaustion becomes the fixed `mime_nesting_too_deep` domain failure. Post-parse traversal is iterative.

Duplicate, missing-value, non-integer, non-positive, overlapping, or inconsistent `rowspan` and `colspan` declarations fail closed.

### Nonreflection and minimization

The public report contains exact source SHA-256/size, hashed Content-Location identity when present, table dimensions, header coordinate/source/count metadata, and fixed diagnostics. It excludes every cell-derived value, decoded HTML, raw Content-ID and Content-Location, location scheme, source-controlled media type, charset, transfer encoding, local path, and resource payload.

Errors and diagnostics expose only stable codes and approved fixed text. Caller-supplied detail, configured limit values, source metadata, and payload text cannot enter public serialization.

The public API and CLI provide no header-value disclosure path. Future schema governance must implement authenticated source custody, protected output, authorization, retention, export approval, and immutable audit before it can access values.

### Semantic catalog handoff

The Semantic Data Portal connector consumes only the value-free schema-proposal
representation. It emits deterministic graph request shapes with fingerprints,
normalized target names, bounded aggregates, and review reasons; it does not
perform HTTP, persist data, attach credentials, or make approval decisions. A
caller-owned boundary must enforce actor identity, tenant authorization,
steward approval, idempotency, retry, TLS, and remote audit before submission.

`semantic_catalog_handoff` makes the actor, tenant reference, approval reference,
and per-request idempotency keys explicit. It does not verify the approval or
send the request. Tenant and approval references stay outside graph-node
properties, and request construction remains free of raw MHTML values.

### PII without destructive masking

Exact business values may remain usable inside future authorized workflows. Compensating controls are tenant isolation, encryption, scoped credentials, row/column authorization, purpose limitation, retention, deletion/legal hold, export approval, immutable audit, and incident response. Public operational artifacts remain value-free.

## Scheduled-agent controls

The hourly workflow:

- runs only from the protected default branch schedule;
- uses a non-cancelling repository-wide concurrency group;
- uses NVIDIA NIM and never references `COPILOT_GITHUB_TOKEN`;
- passes `SHARE: "false"` in both direct OpenCode modes and `share: "disabled"` in repository configuration;
- validates the complete open-PR inventory and uses the lowest-numbered PR only as an initial cursor;
- treats fork heads as read-only and refetches exact live state before writes;
- requires evidence-backed RCA and feasibility proof before mutation;
- reruns only failed or cancelled Actions jobs after source/configuration faults are excluded;
- grants `security-events: read`, never write;
- records one deduplicated external boundary and moves to the next executable item rather than waiting or re-proving it;
- permits at most one additional draft product PR per invocation only after PR repairs/shared blockers are exhausted and fresh non-overlap is proven;
- serializes branch mutation;
- never approves, enables auto-merge, merges, tags, publishes, or releases;
- leaves review, security, branch freshness, and merge to central required workflows.

### Credential isolation

The root-owned `cwl-safe-exec` wrapper is installed before repository-owned gate code runs. It:

- executes as the unprivileged `cwl-untrusted` identity;
- grants repository access only through the dedicated `cwl-workspace` group;
- refuses commands outside `GITHUB_WORKSPACE`;
- creates a clean environment;
- removes NVIDIA, Bytez, OpenRouter, GitHub, OIDC, OpenAI, Anthropic, Google, Strix, OpenCode, and local gateway-token credential variables;
- passes only the non-secret boolean `NVIDIA_NIM_API_KEY_CONFIGURED` marker to gate code;
- is owned by `root:root` and not writable by the agent identity.

OpenCode denies arbitrary shell by default. Repository-controlled Python, tests, package managers, build tools, and scripts run only through the wrapper. Direct environment inspection, direct interpreter/package-manager execution, network-fetch commands, and mutating raw GitHub API forms are not intentionally allowlisted.

Repository source, comments, issues, reviews, logs, and artifacts are untrusted data, never instructions. Copied commands are prohibited. Secret values and environment variables may not be printed, serialized, committed, commented, or transmitted.

### Verified OpenCode executable

The scheduler no longer invokes the upstream composite action because the pinned outer revision still performed a mutable `actions/cache@v4` call, queried the latest release, and executed a network-fetched installer script. Instead, the workflow installs the CLI before any model credential is exposed:

1. require the fixed GitHub-hosted Linux x64 runner profile;
2. select OpenCode version `1.18.15` explicitly;
3. download only `opencode-linux-x64.tar.gz` from the immutable versioned GitHub release URL;
4. require SHA-256 `d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c`, published by the upstream generated Homebrew formula at commit `a72a2bfe3b4114ca10a9012c23f1b3f31924b22e`;
5. verify the digest with `sha256sum --check --strict` before extraction;
6. require the archive to contain exactly one `opencode` entry;
7. extract without preserving archive ownership or permissions;
8. require `opencode --version` to equal `1.18.15` exactly;
9. expose the verified directory to later steps only after every check succeeds;
10. run `opencode github run` directly with credentials only in the selected agent-mode step.

The install step has no NVIDIA, GitHub, or OIDC credential binding. A download, digest, archive-shape, platform, or version mismatch therefore fails before privileged agent execution. No release cache is used; each invocation re-verifies the exact archive. The repository does not claim a separate upstream cryptographic attestation because no offline-verifiable attestation contract has been established for this asset. Changing the version or digest requires a reviewed code change, updated upstream evidence, full contract tests, and rollback to the prior pinned pair if validation fails.

## Supply-chain controls

- GitHub Actions are pinned to full commit SHAs.
- The privileged OpenCode executable is pinned by version, immutable release URL, reviewed SHA-256, archive shape, and exact runtime version.
- The scheduler contains no `curl | bash`, latest-release lookup, mutable nested cache action, or upstream composite installation path.
- The current product runtime has no third-party dependency.
- CI installs its quality-only dependency from a reviewed SHA-256 hash lock in binary-only mode.
- Repository validation recursively scans both `.yml` and `.yaml` workflows for mutable actions and prohibited credentials.
- Agent-branch pushes materialize exact-head CI and share a SHA-keyed concurrency group with same-head PR runs.
- CI compiles, runs exact statement/branch coverage, validates repository contracts, and builds a wheel on Python 3.11–3.14.
- Release maturity requires an SBOM, SLSA provenance, signed artifacts, vulnerability evidence, and reproducible build instructions.

## CSAP and SOC 2 readiness

The architecture supports evidence for asset scope, access, change control, vulnerability management, audit, incident response, backup/recovery, data location, tenant separation, confidentiality, availability, and processing integrity. Certification or attestation can apply only to an assessed deployed service boundary; this repository claims neither.
