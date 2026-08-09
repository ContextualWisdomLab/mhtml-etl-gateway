# Changelog

All notable changes follow Keep a Changelog, and versions follow Semantic Versioning.

## [Unreleased]

### Added

- Dependency-free Python package for bounded MHTML MIME parsing.
- RFC 2387 explicit-root and first-body default-root resolution.
- Non-rendering top-level table extraction with deterministic span normalization.
- Immutable SHA-256 source lineage and metadata-only inspection CLI.
- Content-Location SHA-256 identity without raw location disclosure.
- Synthetic SAP-style, hostile-input, CLI, workflow, privacy, MIME-cardinality, and documentation tests.
- Repository PRD, TRD, architecture, UML/runtime, data-model, conceptual ERD, API, security, threat, test, operating, compliance, roadmap, indexed ADR, research-traceability, and APA 7th doctoring baselines.
- Exact-head Python 3.11–3.14 quality workflow.
- Default-branch-only hourly OpenCode autonomous loop using NVIDIA NIM, exact-head PR maintenance, and a durable `agent-task` lease for empty-queue product work.
- Security regression tests for direct RFC 2387 root selection, cross-media `Content-ID` ambiguity, inert HTML suppression boundaries, configured MIME depth, parser recursion exhaustion, and pre-allocation span budgets.
- Positive `max_mime_depth` resource budget and stable `mime_nesting_too_deep` error contract.
- Root-owned `cwl-safe-exec` wrapper that runs repository-controlled code as a separate unprivileged Linux identity with a clean, secret-free environment.
- Dedicated `cwl-workspace` group that grants the unprivileged identity access only to the repository workspace.
- Granular OpenCode command permissions that deny arbitrary shell execution and permit repository code execution only through `cwl-safe-exec`.
- Work-conserving scheduler contracts that continue from blocked PR actions to other PRs, shared blockers, and one proven-disjoint buyer-visible slice.
- Zero-narration execution contracts that reject status-only termination after one patch, PR, failed remedy, queued check, review delay, or external approval dependency.

### Changed

- Public inspection reports no longer include normalized header text or a CLI header-disclosure option.
- RFC 2387 `type` omission is recorded as `missing_related_type` for known enterprise exports; contradictory declared types fail closed.
- Unknown enterprise Content-Transfer-Encoding values remain an identity-decoding compatibility path with a generic diagnostic.
- MIME part accounting now counts every descendant body entity, including multipart containers, rather than leaves only.
- Post-parse MIME validation traverses iteratively under count and depth budgets.
- The hourly OpenCode workflow explicitly disables session sharing for the public repository.
- An open PR selects deterministic RCA-and-repair mode instead of disabling the hourly loop.
- PR maintenance is work-conserving across the complete open queue: an externally blocked initial PR records one deduplicated boundary and yields to the next independently actionable item while branch mutation remains serialized.
- Existing open PRs no longer form a blanket prohibition on one additional draft product PR when fresh evidence proves complete non-overlap and full verification.
- A gate-clean PR waiting for central merge no longer idles the local loop.
- The autonomous job has read-only code-scanning access so the security-evidence inspection required by its prompt is technically possible.
- Pull-request source, comments, issue bodies, reviews, logs, and artifacts are explicitly treated as untrusted data rather than privileged instructions.
- Repository quality CI runs on `agent/**` pushes and uses the exact head SHA as its concurrency key, so branch writes materialize current-head evidence without duplicating same-SHA pull-request work.
- CI supply-chain contract checks use `unittest.TestCase`, ensuring the repository's actual discovery command executes them.
- The CLI isolates argument-limit `ValueError` handling from inspection-layer domain failures.
- Container-style embedded resources and the void `embed` element now use separate parser policies.

### Fixed

- Default-root selection validates the first direct `multipart/related` body part and never substitutes a nested HTML leaf.
- Explicit `start` duplicates are classified as ambiguous before media-type validation, independent of MIME part order.
- Duplicate critical headers and duplicate `boundary`, `start`, or `type` parameters fail closed before structured parsing can collapse them.
- Defective structured MIME headers that affect root selection fail closed.
- Standard-library recursion exhaustion from extreme MIME nesting becomes the stable, nonreflecting `mime_nesting_too_deep` failure.
- A deeply nested multipart tree with only one leaf can no longer bypass MIME resource limits.
- Mismatched closing tags cannot escape an outer inert `script`, `style`, `noscript`, `template`, `iframe`, or `object` boundary.
- A valid void `<embed>` no longer suppresses all following cell text while its payload and attributes remain ignored.
- Span overlap, trailing rowspans, later-column rowspan gaps, and projected cell allocation are validated deterministically.
- Public errors no longer echo source paths, Content-ID values, charsets, transfer encodings, or declared media types.
- The autonomous scheduler no longer treats review or check latency as a blanket no-op when repository-owned fixes, bounded job reruns, or disjoint product work are feasible.
- A low-numbered PR with only an unchanged external approval or policy dependency can no longer starve later executable work for the entire invocation.
- The repository-owned gate script no longer runs before secret isolation is installed.
- The unprivileged agent identity no longer inherits the runner's default group.

### Security

- Active content, browser rendering, XML entity resolution, office execution, and external resource retrieval are structurally excluded.
- Source bytes, MIME entity count, MIME nesting depth, HTML, table, row, column, cell, cell-text, and normalized-cell budgets fail closed.
- Default reports and logs exclude data rows, header values, raw Content-Location, and embedded resource payloads.
- Customer MHTML artifacts are prohibited from the public repository.
- PII protection uses access, encryption, tenant, lifecycle, export, and audit controls instead of destructive default masking.
- Repository quality CI installs its coverage tool from a reviewed SHA-256 hash lock in pip hash-checking and binary-only mode, and pull-request quality jobs explicitly check out and verify the exact contributor head rather than GitHub's synthetic merge ref.
- PR maintenance validates exact head/base metadata, treats fork heads as read-only, discards stale leases before writes, and never synthesizes approval or weakens central merge gates.
- The secret-stripping wrapper is installed before repository-controlled Python runs; the deterministic gate receives only the non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` marker.
- Repository-controlled tests, builds, package managers, scripts, and gate code cannot inherit the NVIDIA model key, GitHub token, OIDC request token, or other provider credentials from the privileged OpenCode process.
- `cwl-untrusted` receives group access only to `GITHUB_WORKSPACE` through `cwl-workspace`, not through the runner's default group.
- Direct environment inspection, arbitrary shell, direct interpreter/package-manager execution, network-fetch commands, and mutating raw GitHub API calls are denied by the OpenCode permission policy.
