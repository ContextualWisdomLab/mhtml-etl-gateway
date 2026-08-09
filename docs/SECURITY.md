# Security Architecture

## Threat posture

MHTML files are attacker-controlled compound documents. They can carry active HTML, deceptive MIME roots, duplicate identifiers, malformed encodings, oversized or deeply nested structures, internal file URIs, and sensitive customer data. The parser is therefore a data-only trust boundary.

## Implemented controls

### No active execution

The production path has no browser, JavaScript, CSS renderer, office runtime, XML external entity resolver, or resource fetcher. Script/style/noscript/template contents are suppressed while parsing, and exact nested suppression state prevents mismatched closing tags from exposing still-enclosed text.

### MIME ambiguity controls

- parser defects fail closed;
- duplicate critical singleton headers fail closed;
- duplicate `boundary`, `start`, and `type` parameters fail closed from raw header evidence;
- explicit start identifiers resolve across all descendant body entities and must be unique before media-type validation;
- no-start root is the first direct body part, never a later or nested HTML leaf;
- declared type must match the selected root;
- missing type is a visible compatibility diagnostic, not silent conformance.

### MIME recursion and entity budgets

The standard-library email parser can recurse while constructing deeply nested multipart input. The public boundary catches recursion exhaustion and returns the stable, nonreflecting `mime_nesting_too_deep` error. After parsing, the gateway traverses the MIME tree iteratively and enforces:

- `max_mime_depth` across nested body entities;
- `max_mime_parts` across all descendant entities, including multipart containers;
- `max_source_bytes` before parsing.

This prevents a one-leaf, deeply nested document from bypassing the former leaf-count-only resource control or escaping as an unstructured `RecursionError`.

### Other resource controls

Decoded HTML characters, tables, rows, columns, normalized cells, and cell text all have independent positive bounds. Span-created implicit rows and cells consume the same budgets.

### Nonreflection and minimization

Default reports omit every cell value. Raw Content-Location is replaced with scheme plus SHA-256. Errors and diagnostics do not repeat source paths, identifiers, charset names, transfer encodings, declared media types, payload text, or attacker-selected boundary values.

### PII without destructive masking

Exact business values remain available only to authorized workflows. Compensating controls are tenant isolation, encryption, scoped credentials, row/column authorization, purpose limitation, retention, deletion/legal hold, export approval, immutable audit, and incident response. Metadata artifacts are designed so ordinary operations do not need raw values.

## Scheduled-agent controls

The hourly workflow:

- runs only from the protected default branch schedule;
- uses a non-cancelling repository-wide concurrency group;
- requires `NVIDIA_NIM_API_KEY` and never references `COPILOT_GITHUB_TOKEN`;
- sets OpenCode `share: false` in both maintenance and product-development modes;
- selects the lowest-numbered open PR from validated exact-head metadata when a PR exists;
- treats fork PR heads as read-only;
- requires RCA and proof that a proposed remedy is technically feasible before mutation;
- refetches the live head immediately before writes and discards stale leases;
- permits bounded retries only for failed or cancelled Actions work after code/configuration faults are excluded;
- creates or resumes one durable `agent-task` only when the PR queue is empty;
- never approves, merges, enables auto-merge, tags, publishes, or releases;
- leaves review and merge to central required workflows.

## Supply-chain controls

- GitHub Actions are pinned to full commit SHAs.
- Runtime has no third-party dependency in the first slice.
- CI installs its quality-only dependency from a reviewed SHA-256 hash lock in binary-only mode.
- The dependency-integrity contract is implemented as `unittest.TestCase`, so the active discovery command executes it.
- Agent-branch pushes materialize exact-head CI and share a SHA-keyed concurrency group with same-head PR runs.
- CI compiles, tests with exact line/branch coverage, validates repository contracts, and builds a wheel.
- Release maturity requires SBOM, SLSA provenance, signed artifacts, vulnerability evidence, and reproducible build instructions.

## CSAP and SOC 2 readiness

The architecture supports evidence for asset scope, access, change control, vulnerability management, audit, incident response, backup/recovery, data location, tenant separation, confidentiality, availability, and processing integrity. Certification or attestation can apply only to an assessed deployed service boundary; this repository does not claim either.
