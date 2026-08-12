# Entity Relationship and Evidence Model

**Status:** Accepted model for current transactional artifact loads and future governed ingestion entities.
**Last reviewed:** 2026-08-09

This ERD intentionally separates **current in-memory inspection objects and
transactional dynamic load tables** from **future persisted ingestion control
entities**. The current loader creates the artifact catalog and caller-selected
business table; the future section is not evidence that staging migrations,
RLS policies, or an asynchronous service already exists.

## Current in-memory model

```mermaid
classDiagram
    class ParseLimits {
      +max_source_bytes
      +max_mime_parts
      +max_mime_depth
      +max_html_chars
      +max_tables
      +max_rows_per_table
      +max_columns_per_table
      +max_raw_cells
      +max_normalized_cells
      +max_cell_text_chars
    }
    class MhtmlDocument {
      +decoded_html
      +protected_root_metadata
      +diagnostics
    }
    class ExtractedTable {
      +logical_cells
      +row_count
      +column_count
      +header_source
      +diagnostics
    }
    class InspectionReport {
      +source_hash_sha256
      +source_size_bytes
      +root_content_location_hash_sha256
      +table_summaries
      +diagnostics
    }

    ParseLimits --> MhtmlDocument : bounds parsing
    MhtmlDocument --> ExtractedTable : authoritative HTML only
    ExtractedTable --> InspectionReport : value-free summary
```

`MhtmlDocument` and `ExtractedTable` may contain protected values in process memory. `InspectionReport` intentionally does not serialize header or row values.

## Current value-free catalog handoff

```mermaid
classDiagram
    class SchemaProposal {
      +schema_proposal_id
      +proposal_version
      +source_hash_sha256
      +table_fingerprint_sha256
      +columns
    }
    class SemanticCatalogManifest {
      +manifest_id
      +contract_version
      +nodes
      +edges
      +privacy_mode = value_free
    }
    class CatalogNode {
      +node_id
      +kind
      +label
      +properties
    }
    class CatalogEdge {
      +edge_type
      +source_id
      +target_id
      +properties
    }
    class CatalogSubmissionEnvelope {
      +envelope_id
      +contract_version
      +target_system
      +manifest_id
      +tenant_id
      +actor
      +approval_reference
      +requests
    }
    class CatalogWriteRequest {
      +method
      +path
      +idempotency_key
      +body
    }

    SchemaProposal --> SemanticCatalogManifest : deterministic conversion
    SemanticCatalogManifest "1" --> "1..*" CatalogNode : emits
    SemanticCatalogManifest "1" --> "0..*" CatalogEdge : emits
    SemanticCatalogManifest --> CatalogSubmissionEnvelope : governed handoff
    CatalogSubmissionEnvelope "1" --> "1..*" CatalogWriteRequest : plans
```

This is an in-memory contract, not a database migration. The manifest can be
submitted by a caller to the Semantic Data Portal graph API only after the
caller performs authentication, tenant authorization, and steward approval.
The submission envelope is still a plan: remote acceptance is not represented.

## Future conceptual PostgreSQL ERD

The following entities are target architecture for governed ingestion. Schema names are shown as prefixes for clarity. All database objects must use descriptive two-or-more-word `snake_case` names.

```mermaid
erDiagram
    RAW_IMPORT_SOURCE_ARTIFACT ||--o{ RAW_IMPORT_IMPORT_JOB : requested_by
    RAW_IMPORT_SOURCE_ARTIFACT ||--o{ RAW_IMPORT_SOURCE_TABLE : contains
    RAW_IMPORT_SOURCE_TABLE ||--o{ RAW_IMPORT_SOURCE_ROW : contains

    RAW_IMPORT_IMPORT_JOB ||--o{ STAGING_DATA_SCHEMA_PROPOSAL : evaluates
    STAGING_DATA_SCHEMA_PROPOSAL ||--o{ STAGING_DATA_COLUMN_PROPOSAL : contains
    STAGING_DATA_SCHEMA_PROPOSAL ||--o{ AUDIT_LOG_POLICY_DECISION : governed_by

    RAW_IMPORT_SOURCE_ROW ||--o{ STAGING_DATA_STAGING_RECORD : transforms_to
    STAGING_DATA_STAGING_RECORD ||--o{ STAGING_DATA_VALIDATION_ERROR : may_have
    STAGING_DATA_STAGING_RECORD ||--o{ AUDIT_LOG_LINEAGE_EDGE : source_side

    RAW_IMPORT_IMPORT_JOB ||--o{ AUDIT_LOG_AUDIT_EVENT : emits
    RAW_IMPORT_IMPORT_JOB ||--o{ AUDIT_LOG_RECONCILIATION_RESULT : reconciles
    STAGING_DATA_SCHEMA_PROPOSAL ||--o{ AUDIT_LOG_AUDIT_EVENT : emits
    AUDIT_LOG_POLICY_DECISION ||--o{ AUDIT_LOG_AUDIT_EVENT : records

    RAW_IMPORT_SOURCE_ARTIFACT {
      uuid source_artifact_id PK
      uuid tenant_record_id
      text source_hash_sha256 UK
      bigint source_size_bytes
      text media_type_code
      text encryption_key_ref
      text retention_class_code
      boolean legal_hold_active
      timestamptz created_at
    }

    RAW_IMPORT_IMPORT_JOB {
      uuid import_job_id PK
      uuid tenant_record_id
      uuid source_artifact_id FK
      text idempotency_key UK
      text requested_operation_code
      text import_status_code
      uuid requested_schema_proposal_id
      uuid actor_identity_id
      timestamptz created_at
      timestamptz updated_at
    }

    RAW_IMPORT_SOURCE_TABLE {
      uuid source_table_id PK
      uuid source_artifact_id FK
      integer table_ordinal
      text structural_fingerprint
      bigint source_row_count
      integer source_column_count
      text parser_version
    }

    RAW_IMPORT_SOURCE_ROW {
      uuid source_row_id PK
      uuid source_table_id FK
      bigint source_row_number
      text protected_payload_ref
      text source_row_hash
    }

    STAGING_DATA_SCHEMA_PROPOSAL {
      uuid schema_proposal_id PK
      uuid import_job_id FK
      integer proposal_version
      text proposal_status_code
      text source_header_bundle_hash
      text schema_contract_hash
      uuid approved_by_identity_id
      timestamptz approved_at
    }

    STAGING_DATA_COLUMN_PROPOSAL {
      uuid column_proposal_id PK
      uuid schema_proposal_id FK
      integer source_column_ordinal
      text source_column_fingerprint
      text target_column_name
      text target_type_code
      text nullability_code
      numeric confidence_score
      text policy_outcome_code
    }

    STAGING_DATA_STAGING_RECORD {
      uuid staging_record_id PK
      uuid import_job_id FK
      uuid source_row_id FK
      text approved_schema_hash
      text protected_record_ref
      text validation_status_code
    }

    STAGING_DATA_VALIDATION_ERROR {
      uuid validation_error_id PK
      uuid staging_record_id FK
      uuid column_proposal_id FK
      text error_code
      text protected_detail_ref
      bigint source_row_number
      integer source_column_ordinal
    }

    AUDIT_LOG_AUDIT_EVENT {
      uuid audit_event_id PK
      uuid tenant_record_id
      uuid import_job_id FK
      uuid actor_identity_id
      text action_code
      text resource_type_code
      uuid resource_record_id
      text outcome_code
      uuid correlation_record_id
      text protected_evidence_ref
      timestamptz occurred_at
    }

    AUDIT_LOG_LINEAGE_EDGE {
      uuid lineage_edge_id PK
      uuid tenant_record_id
      uuid source_row_id FK
      uuid staging_record_id FK
      text normalized_object_type
      uuid normalized_object_id
      text parser_version
      text schema_contract_hash
      text loader_version
    }

    AUDIT_LOG_RECONCILIATION_RESULT {
      uuid reconciliation_result_id PK
      uuid import_job_id FK
      bigint source_row_count
      bigint accepted_row_count
      bigint rejected_row_count
      bigint duplicate_row_count
      bigint target_row_count
      text balance_status_code
      timestamptz measured_at
    }

    AUDIT_LOG_POLICY_DECISION {
      uuid policy_decision_id PK
      uuid schema_proposal_id FK
      text policy_version
      text policy_input_hash
      text decision_code
      text reason_code
      uuid deciding_identity_id
      timestamptz decided_at
    }
```

## Generated normalized domain tables

`normalized_data` tables are **not** represented as one fixed generic table because their columns are created only from an approved schema artifact. Examples such as `inspection_document`, `customer_case_record`, or `quality_action_record` are illustrative domain names, not current migrations.

Every generated normalized row must expose an opaque row identifier and be reachable through `audit_log.lineage_edge`. The lineage edge carries version evidence; it does not copy protected business values into the audit schema.

## Tenant and authorization invariants

- Every persisted operational entity is tenant-bound directly or through a parent whose tenant is transactionally enforced.
- Natural SAP/customer identifiers are business values, never authorization keys.
- Cross-service external identifiers use RFC 9562 UUIDv7 but their timestamps have no authorization semantics.
- PostgreSQL RLS, service authorization, encryption, and protected views are planned enforcement layers and must be proven in migrations/tests before this document can classify them as implemented.
- Audit and lineage records may survive protected-payload retention expiry when policy allows, but must not retain the expired raw values themselves.

## Lineage invariant

```mermaid
flowchart LR
    N[normalized domain row] --> L[lineage_edge]
    L --> S[staging_record]
    S --> R[source_row]
    R --> T[source_table]
    T --> A[source_artifact]
    L --> V[parser / schema / loader versions]
    A --> H[immutable source SHA-256]
```

A future `completed` import is invalid unless source, accepted, rejected, duplicate, and target counts reconcile under the approved load policy and every accepted normalized row has a complete lineage path.

## Migration acceptance for future persistence

Before any conceptual entity becomes an as-built table, the implementing PR must include: migration and rollback, tenant/RLS tests, constraints and indexes, transaction/concurrency tests, idempotent replay, protected-value/logging tests, lineage/reconciliation tests, backup/recovery impact, and an ADR or existing ADR mapping. This ERD must then be updated from conceptual to as-built status for the affected entities.
