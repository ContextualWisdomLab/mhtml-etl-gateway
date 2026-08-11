# Data Model

## Current in-memory contracts

- `MhtmlDocument`: decoded authoritative root plus protected internal MIME metadata.
- `ExtractedTable`: rectangular logical cells retained only in process memory.
- `InspectionReport`: nonreflecting public metadata.
- `ParseLimits`: explicit resource budgets.
- `Diagnostic`: fixed-code nonfatal evidence.

Data rows are intentionally absent from the serialized inspection model.

## Future PostgreSQL schemas

All names contain at least two words and use `snake_case`.

### `raw_import`

- `source_artifact`: immutable object-store identity, tenant, content hash, byte size, media type, encryption key reference, retention class, legal-hold state, and creation time.
- `import_job`: requested operation, idempotency key, source artifact, requested mapping, status, and actor.
- `source_table`: table ordinal, structural fingerprint, row/column counts, and parser version.
- `source_row`: protected row artifact reference and original row coordinate; row values are not copied into audit logs.

### `staging_data`

- `schema_proposal`: versioned proposal and approval state.
- `column_proposal`: source fingerprint, normalized target name, proposed type, nullability/type evidence, confidence, and policy outcome.
- `staging_record`: typed candidate record linked to source row.
- `validation_error`: stable error code, source coordinate, target column identifier, and protected detail reference.

### `normalized_data`

Domain tables are created only from approved artifacts. Example names include `inspection_document`, `customer_case_record`, and `quality_action_record`. Generic one-word names such as `data`, `user`, `log`, or `record` are prohibited.

### `audit_log`

- `audit_event`: actor, action, resource, outcome, time, correlation ID, and protected evidence reference.
- `lineage_edge`: source artifact/table/row to staging and normalized object relationship.
- `reconciliation_result`: source, accepted, rejected, target, and duplicate counts.
- `policy_decision`: policy version, inputs by hash, outcome, reason code, and approving actor.

## Identifier policy

External and cross-service IDs use UUIDv7 according to RFC 9562. Database surrogate identifiers are never sequentially exposed. Natural SAP identifiers remain business values and are never used as tenant authorization boundaries.

## PII policy

Operational values may be stored exactly when authorized. Access is controlled by tenant keying, PostgreSQL row-level security, column privileges or protected views, application authorization, encryption, purpose/retention policy, and audit. Logs and metrics contain identifiers by opaque ID or keyed hash, not raw values.

## Lineage invariant

Every normalized row must trace to:

```text
normalized row
  -> staging record
  -> source row coordinate
  -> source table ordinal
  -> source artifact SHA-256
  -> parser, mapping, policy, and loader versions
```

Deletion, retention expiry, or legal hold changes the availability of protected payloads but not the integrity of the allowed lineage record.
