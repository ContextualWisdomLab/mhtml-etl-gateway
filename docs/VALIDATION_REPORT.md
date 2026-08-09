# Validation Report

**Validated:** 2026-08-09
**Product version:** 0.1.0
**Scope:** deterministic MHTML inspection baseline and autonomous-maintenance contracts

## Test and coverage evidence

A fresh reconstruction of the current production, test, script, dependency-lock, and workflow files produced:

```text
130 tests passed
728 production statements: 100%
272 production branches: 100%
Missing public production docstrings: 0
```

Coverage includes the shipped package and production workflow helper scripts. Tests cover MIME root/cardinality/defect handling, strict decoding, direct RFC 2387 default-root selection, cross-media `Content-ID` ambiguity, inert HTML suppression boundaries, table normalization, privacy nonreflection, CLI behavior, realistic SAP-shaped input, repository governance, exact-head CI, and hourly autonomous-loop contracts.

The CI dependency-integrity checks are implemented as `unittest.TestCase` methods so the repository's actual `python -m unittest discover` command executes them. They verify the hash-locked coverage dependency, binary-only pip mode, contributor-head checkout, and exact-head assertion.

## Static and repository evidence

- `python -m compileall -q src tests scripts`: passed
- `PYTHONPATH=src python scripts/validate_repository.py`: passed
- required document inventory: complete
- unresolved template-marker tokens in required documents: 0
- mutable GitHub Action references: 0
- prohibited `COPILOT_GITHUB_TOKEN` workflow references: 0
- committed `.mhtml` or `.mht` artifacts: 0
- hourly NIM secret binding: present
- OpenCode public-session sharing: disabled with `share: false`
- agent-branch quality execution: enabled for `agent/**`
- push and pull-request quality concurrency: keyed by exact head SHA

## Parser security regression evidence

The current source includes focused regressions proving that:

- a nested HTML leaf cannot replace a non-HTML first direct `multipart/related` body part;
- duplicate explicit `start` identifiers remain ambiguous regardless of MIME part ordering or media type;
- a mismatched closing suppressed tag cannot expose text still enclosed by an outer `script`, `style`, `noscript`, or `template` element;
- ordinary non-table elements do not create table structure.

Focused verification also independently produced:

```text
MIME parser: 38 tests; 161 statements; 80 branches; 100%
HTML table parser: 36 tests; 202 statements; 94 branches; 100%
Hourly scheduler: 107 statements; 40 branches; 100%
CI dependency integrity: 2 tests passed
```

## Package evidence

Wheel:

```text
mhtml_etl_gateway-0.1.0-py3-none-any.whl
```

The wheel builds without runtime dependencies and includes:

- `mhtml_etl_gateway/py.typed`;
- the Apache-2.0 license under `.dist-info/licenses/`;
- the console entry point;
- package version 0.1.0.

A clean virtual environment previously installed the wheel without an index and passed package and CLI smoke tests. A release still requires fresh exact-head package evidence, SBOM, signed provenance, and protected-branch merge.

## Protected real-export evidence

A noncommitted operator-held MHTML export was inspected without printing or committing its filename, path, source hash, header values, or row values. Its protected local receipt recorded only these aggregate results for this public document:

```text
table_count: 1
row_count: 14
data_row_count: 13
column_count: 40
header_value_count: 40
default_header_values_included: false
root_content_location_scheme: file
document_diagnostics: identity_transfer_encoding, missing_related_type
table_diagnostics: positional_header
```

Assertions confirmed that the default report contains no header values, raw file location, drive path, source hash disclosure in this public artifact, or row values. A separate protected opt-in inspection confirmed that 40 header values are available to an authorized schema-design workflow without serializing data rows.

## GitHub evidence boundary

Local verification does not replace GitHub required checks. Every head-changing commit must receive current-head repository quality, central security, SAST, independent review, and unresolved-thread evidence. Queued, pending, skipped-required, cancelled, absent, predecessor-head, or synthetic-merge-only results are not passing evidence.

## Release assessment

The implementation is suitable for continued review as the first pre-1.0 product slice. It is not yet a PostgreSQL ETL release: schema proposals, approval, database migrations, transactional `COPY FROM STDIN`, reconciliation, tenancy, service API, SBOM, signed provenance, and deployment evidence remain later milestones. Version 0.1.0 should be released only after the exact PR head passes organization required checks, independent review, unresolved-thread policy, and protected-branch merge.
