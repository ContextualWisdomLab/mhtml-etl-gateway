# Validation Report

**Validated:** 2026-08-07
**Product version:** 0.1.0
**Scope:** deterministic MHTML inspection baseline

## Test and coverage evidence

```text
114 tests passed
675 production statements: 100%
252 production branches: 100%
Missing public production docstrings: 0
```

Coverage includes the shipped package and production workflow helper scripts. Tests cover MIME root/cardinality/defect handling, strict decoding, table normalization, privacy nonreflection, CLI behavior, realistic SAP-shaped input, repository governance, and hourly workflow contracts.

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

## Package evidence

Wheel:

```text
mhtml_etl_gateway-0.1.0-py3-none-any.whl
size: 16,438 bytes
```

The wheel built without runtime dependencies. Its build-instance SHA-256 was recorded in the protected local verification receipt rather than committed as a reproducibility claim; deterministic release artifacts remain a later milestone. Archive inspection confirmed:

- `mhtml_etl_gateway/py.typed`;
- Apache-2.0 license under `.dist-info/licenses/`;
- console entry point;
- package version 0.1.0.

A clean virtual environment installed the wheel without an index and passed package and CLI smoke tests.

## Protected real-export evidence

A noncommitted operator-held MHTML export was inspected without printing or committing its filename, path, source hash, header values, or row values. Its local receipt matched the expected protected identity and recorded only these aggregate results for this public document:

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

## Release assessment

The implementation is suitable for review as the first pre-1.0 product slice. It is not yet a PostgreSQL ETL release: schema proposals, approval, database migrations, transactional COPY, reconciliation, tenancy, service API, SBOM, signed provenance, and deployment evidence remain later milestones. Version 0.1.0 should be released only after the exact PR head passes organization required checks, independent review, unresolved-thread policy, and protected-branch merge.
