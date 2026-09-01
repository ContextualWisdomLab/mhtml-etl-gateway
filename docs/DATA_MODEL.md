# Data Model

## Current in-memory contracts

- `MhtmlDocument`: decoded authoritative root plus protected internal MIME metadata.
- `ExtractedTable`: rectangular logical cells retained only in process memory.
- `InspectionReport`: nonreflecting public metadata.
- `ParseLimits`: explicit resource budgets.
- `Diagnostic`: fixed-code nonfatal evidence.
- `SchemaProposal`: ordered, content-addressed, value-free proposed columns.
- `propose_schema_from_mhtml`: local source-custody wrapper that converts one
  validated MHTML table into the existing `SchemaProposal` without a write or
  network side effect.
- `SemanticCatalogManifest`: deterministic dataset/column graph handoff with no
  network or persistence authority.
- `CatalogSubmissionEnvelope`: deterministic, value-free actor/tenant/approval
  handoff with ordered portal request plans and idempotency keys.
- `CatalogPublisherEvidence`: caller-provided proof of authentication,
  authorization, approval verification, and immutable audit correlation.
- `CatalogTransportResponse`: explicit remote status, acceptance, and opaque
  request identity returned by a caller-owned transport.
- `CatalogPublicationReceipt`: value-free remote-acceptance evidence for the
  complete submission, with safe per-request receipts and no request bodies.
- `PgErdVisualizationPlan`: deterministic, value-free DBML conversion request
  plan for one proposed table, without transport or persistence authority.

Data rows are intentionally absent from the serialized inspection model.

### Semantic catalog handoff

`SemanticCatalogManifest` contains a dataset node, column nodes, and
`contains_column` edges. Node properties carry proposal IDs, source/header
fingerprints, types, nullability, bounded aggregate evidence, and review
reasons. It contains no raw source headers or sample values. Actor identity,
tenant policy, approval, and transport credentials remain outside this
in-memory contract.

### Governed catalog handoff

`CatalogSubmissionEnvelope` contains `envelope_id`, `contract_version`,
`target_system`, `manifest_id`, `tenant_id`, `actor`,
`approval_reference`, and ordered `CatalogWriteRequest` objects. Each request
contains a portal path, `POST` method, actor-bearing body, and deterministic
idempotency key scoped by tenant and approval reference. The envelope is a
plan, not a remote-acceptance record; envelope and request IDs are only
correlation/deduplication evidence. Credential binding, actor authentication,
approval verification, tenant authorization, TLS, retry, remote acceptance,
and immutable audit remain caller-owned.

### Governed catalog publication

`CatalogPublisherEvidence` records only four required governance assertions and
an opaque immutable audit reference. `CatalogTransportResponse` accepts only a
2xx status, explicit `accepted=True`, and an opaque remote request ID.
`CatalogPublicationReceipt` records the envelope ID, target, audit reference,
accepted request count, and ordered `CatalogRequestReceipt` values containing
request index, path, idempotency key, status, and remote request ID. Request
bodies, source values, credentials, and provider error bodies are excluded.
Partial acceptance is an error with only the accepted prefix count; it is not a
complete publication receipt.

### pg-erd-cloud visualization plan

`PgErdVisualizationPlan` contains the connector contract version, target
system, source/proposal identity, and a request body with DBML, PostgreSQL
dialect, and `include_ddl=false`. The DBML contains one table, proposal target
columns, allow-listed types, and optional `[not null]` settings. It has no
samples, comments, records, or inferred relationships. It is a request plan,
not a diagram snapshot or remote-acceptance record.

## Future PostgreSQL schemas

All names contain at least two words and use `snake_case`.

### `raw_import`

- `source_artifact`: immutable object-store identity, tenant, content hash, byte size, media type, encryption key reference, retention class, legal-hold state, and creation time.
- `import_job`: requested operation, idempotency key, source artifact, requested mapping, import status, and actor.
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

Every generated table and column name is lowercase multiword `snake_case` and
fits PostgreSQL's 63-byte unquoted-identifier limit. Single-token columns use
`_field`, single-token tables use `_table`, and direct unsafe names are rejected
before DDL. The Python `CatalogEntry.load_status_code` state now matches the SQL
catalog column `load_status_code`. `CatalogEntry.to_dict()` deliberately emits
the established `status` wire key only at the serialization compatibility
boundary, and the idempotent database migration still translates older
persisted `status` columns to `load_status_code`.

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
