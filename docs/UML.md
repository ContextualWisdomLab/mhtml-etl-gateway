# UML and Runtime Views

**Status:** Accepted documentation baseline for the current inspection and
value-free catalog-handoff slices; persisted ingestion boundaries remain future.
**Last reviewed:** 2026-08-11

This document is the canonical diagram-as-code view of MHTML ETL Gateway. A box labelled **future** is target architecture, not a claim that the component is implemented or deployable today. Current production behavior includes value-free schema proposals and a caller-owned Semantic Data Portal manifest handoff; persisted ingestion services remain future.

## Component view

```mermaid
flowchart LR
    subgraph current[Current deterministic inspection package]
        CLI[cli]
        MOD[models]
        ERR[errors]
        MIME[mime_parser]
        HTML[html_tables]
        INS[inspection]
        CLI --> INS
        INS --> MIME
        INS --> HTML
        MIME --> MOD
        HTML --> MOD
        MIME --> ERR
        HTML --> ERR
    INS --> MOD
        PROPOSAL[schema_proposal]
        CATALOG[semantic_catalog_connector]
        INS --> PROPOSAL
        PROPOSAL --> CATALOG
    end

    SRC[Untrusted MHTML bytes] --> CLI
    INS --> REPORT[Value-free InspectionReport]

    subgraph future[Future governed ingestion services]
        CUST[source_custody_service]
        SCHEMA[schema_governance_service]
        LOAD[postgres_load_service]
        AUDIT[audit_and_observability]
        STORE[(PostgreSQL)]
    end

    REPORT -. protected evidence reference .-> CUST
    CATALOG -. value-free nodes and edges .-> PORTAL[semantic-data-portal]
    CUST -. authenticated header/value evidence .-> SCHEMA
    SCHEMA -. approved schema artifact .-> LOAD
    LOAD -. transaction and COPY .-> STORE
    CUST -. audit .-> AUDIT
    SCHEMA -. audit .-> AUDIT
    LOAD -. reconciliation .-> AUDIT
```

### Boundary rules

- Current parser code has no browser, JavaScript, network fetch, Office runtime, XML external-entity, shell, database, or connector capability.
- Header/value disclosure is not added to `InspectionReport`; future schema work uses a separate authenticated source-custody boundary.
- The future loader accepts only an approved, versioned schema artifact and scoped database authorization.
- `pg-erd-cloud`, naruon, pg-llm-batch, and contextual-orchestrator are downstream/optional integration ports, not hidden runtime dependencies of the parser.

## Inspection sequence

```mermaid
sequenceDiagram
    actor Operator
    participant CLI as cli
    participant Inspect as inspection
    participant Mime as mime_parser
    participant Table as html_tables
    participant Report as InspectionReport

    Operator->>CLI: inspect(source bytes, ParseLimits)
    CLI->>Inspect: inspect_mhtml_bytes(...)
    Inspect->>Inspect: enforce source budget + SHA-256
    Inspect->>Mime: parse bounded MIME container
    Mime->>Mime: validate defects, duplicate metadata, count/depth
    Mime->>Mime: resolve RFC 2387 root
    Mime->>Mime: strict charset/BOM/UTF-8 decode
    Mime-->>Inspect: authoritative decoded HTML + protected metadata
    Inspect->>Table: extract top-level tables
    Table->>Table: suppress inert containers
    Table->>Table: project spans before allocation
    Table->>Table: normalize rectangular grid
    Table-->>Inspect: in-memory ExtractedTable values
    Inspect->>Inspect: derive value-free structural metadata
    Inspect-->>Report: hash/location/table shape/diagnostics only
    Report-->>CLI: serializable public result
    CLI-->>Operator: JSON without cell-derived values
```

## Current parser state view

```mermaid
stateDiagram-v2
    [*] --> SourceBounded
    SourceBounded --> MimeValidated: source within limit
    SourceBounded --> Failed: source budget exceeded
    MimeValidated --> RootResolved: unique valid root
    MimeValidated --> Failed: defects / duplicate metadata / depth / ambiguity
    RootResolved --> HtmlDecoded: strict decode succeeds
    RootResolved --> Failed: root/type/charset invalid
    HtmlDecoded --> TablesProjected: top-level tables parsed
    HtmlDecoded --> Failed: HTML/table budget or structure invalid
    TablesProjected --> TablesNormalized: projected allocation remains within limits
    TablesProjected --> Failed: span overlap / expansion budget invalid
    TablesNormalized --> Reported: value-free report derived
    TablesNormalized --> Failed: realization differs from projection
    Reported --> [*]
    Failed --> [*]
```

`Failed` represents a stable `MhtmlGatewayError` code for expected input failures. Unexpected programming defects remain defects; they are not rewritten into successful or ambiguous results.

## Future import-job state view

The following lifecycle is **conceptual P1-P3 target architecture**. No current persisted `import_job` table or service state machine is claimed.

```mermaid
stateDiagram-v2
    [*] --> created
    created --> source_registered
    source_registered --> inspecting
    inspecting --> schema_review: structure accepted
    inspecting --> failed: deterministic inspection failed
    schema_review --> schema_approved: steward/policy approval
    schema_review --> rejected: proposal rejected
    schema_approved --> validating
    validating --> loading: candidate rows valid for load policy
    validating --> failed: validation cannot continue
    loading --> reconciling
    loading --> failed: transaction/load failure
    reconciling --> completed: counts + lineage balance
    reconciling --> rollback_required: imbalance or post-load failure
    rollback_required --> rolled_back
    rolled_back --> failed
    created --> cancelled
    source_registered --> cancelled
    schema_review --> cancelled
    completed --> [*]
    failed --> [*]
    rejected --> [*]
    cancelled --> [*]
```

A future implementation must make every transition idempotent or transactionally guarded, retain the exact source/mapping/parser/loader versions, and never mark `completed` while reconciliation is unbalanced.

## Deployment view

```mermaid
flowchart TB
    subgraph embedded[Mode A — embedded library, current]
        APP[Caller process]
        LIB[mhtml_etl_gateway package]
        APP --> LIB
    end

    subgraph single[Mode B — future single-node service]
        API[authenticated intake/API]
        WORKER[parser + validation worker]
        OBJ[(encrypted object storage)]
        PG[(PostgreSQL)]
        API --> OBJ
        API --> WORKER
        WORKER --> OBJ
        WORKER --> PG
    end

    subgraph msa[Mode C — future modular MSA]
        INTAKE[source_intake_service]
        PARSER[mhtml_parser_service\nno egress]
        GOVERN[schema_governance_service]
        LOADER[postgres_load_service]
        OBS[audit_observability_service]
        DB[(PostgreSQL)]
        INTAKE --> PARSER
        PARSER --> GOVERN
        GOVERN --> LOADER
        LOADER --> DB
        INTAKE --> OBS
        PARSER --> OBS
        GOVERN --> OBS
        LOADER --> OBS
    end
```

## Authority flow

```mermaid
flowchart LR
    USER[Authorized operator] -->|submit exact source| CUST[Source custody authority]
    CUST -->|immutable bytes / bounded parse request| PARSE[Deterministic parser]
    PARSE -->|structural evidence only| GOV[Schema governance]
    STEWARD[Data steward or approved policy] -->|approve/reject proposal| GOV
    GOV -->|signed/versioned approved schema| LOAD[Loader authority]
    DBROLE[Scoped tenant DB role] -->|least-privilege credential| LOAD
    LOAD -->|staging + COPY + reconcile| DB[(Tenant PostgreSQL)]
    CUST --> AUDIT[Audit evidence]
    GOV --> AUDIT
    LOAD --> AUDIT
```

No LLM, downstream service, or visualization tool may promote an unapproved proposal into loader authority. Future AI assistance may explain or review evidence but cannot mutate immutable source identity or bypass deterministic validation and schema approval.

## Diagram maintenance contract

Update this file when a material component, authority boundary, externally visible lifecycle, or deployment topology changes. Corresponding ADR, PRD/TRD, data model, API contract, threat model, tests, and CHANGELOG must be reconciled in the same change when affected.
