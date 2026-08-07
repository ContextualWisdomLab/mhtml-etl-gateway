# Security Architecture

## Threat posture

MHTML files are attacker-controlled compound documents. They can carry active HTML, deceptive MIME roots, duplicate identifiers, malformed encodings, oversized structures, internal file URIs, and sensitive customer data. The parser is therefore a data-only trust boundary.

## Implemented controls

### No active execution

The production path has no browser, JavaScript, CSS renderer, office runtime, XML external entity resolver, or resource fetcher. Script/style/noscript/template contents are suppressed while parsing.

### MIME ambiguity controls

- parser defects fail closed;
- duplicate critical singleton headers fail closed;
- duplicate `boundary`, `start`, and `type` parameters fail closed from raw header evidence;
- explicit start identifiers resolve across all leaf parts and must be unique HTML;
- no-start root is the first body part;
- declared type must match the selected root;
- missing type is a visible compatibility diagnostic, not silent conformance.

### Resource controls

Source bytes, MIME parts, decoded HTML characters, tables, rows, columns, cells, and cell text all have independent positive bounds. Span-created implicit rows and cells consume the same budgets.

### Nonreflection and minimization

Default reports omit every cell value. Raw Content-Location is replaced with scheme plus SHA-256. Errors and diagnostics do not repeat source paths, identifiers, charset names, transfer encodings, declared media types, or payload text.

### PII without destructive masking

Exact business values remain available only to authorized workflows. Compensating controls are tenant isolation, encryption, scoped credentials, row/column authorization, purpose limitation, retention, deletion/legal hold, export approval, immutable audit, and incident response. Metadata artifacts are designed so ordinary operations do not need raw values.

## Scheduled-agent controls

The hourly workflow:

- runs only from the protected default branch schedule;
- uses a non-cancelling repository-wide concurrency group;
- requires `NVIDIA_NIM_API_KEY` and never references `COPILOT_GITHUB_TOKEN`;
- sets OpenCode `share: false`;
- uses a durable `agent-task` issue lease;
- refuses to dispatch while any PR is open or multiple task leases exist;
- creates at most one bounded PR;
- cannot merge or release;
- leaves review and merge to central required workflows.

## Supply-chain controls

- GitHub Actions are pinned to full commit SHAs.
- Runtime has no third-party dependency in the first slice.
- CI compiles, tests with line/branch coverage, validates repository contracts, and builds a wheel.
- Release maturity requires SBOM, SLSA provenance, signed artifacts, vulnerability evidence, and reproducible build instructions.

## CSAP and SOC 2 readiness

The architecture supports evidence for asset scope, access, change control, vulnerability management, audit, incident response, backup/recovery, data location, tenant separation, confidentiality, availability, and processing integrity. Certification or attestation can apply only to an assessed deployed service boundary; this repository does not claim either.
