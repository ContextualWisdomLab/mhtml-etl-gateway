# pg-erd-cloud visualization connector

The gateway can now turn an existing value-free `SchemaProposal` into a
transport-neutral request plan for `ContextualWisdomLab/pg-erd-cloud`'s
`POST /api/dbml/convert` route. This closes the buyer-facing gap between
reviewing an inferred schema and opening that schema in a database diagram.

## Python contract

```python
from mhtml_etl_gateway import build_pg_erd_visualization_plan

plan = build_pg_erd_visualization_plan(
    schema_proposal,
    catalog_name="SAP VOC export",
)
request = plan.to_dict()["request"]
```

The request body contains only:

```json
{
  "dbml": "Table sap_voc_export {\n  client_code text [not null]\n}",
  "include_ddl": false,
  "dialect": "postgresql"
}
```

The generated DBML uses the documented `Table`, column, and `not null`
constructs. Column names are checked with the gateway's existing multiword
`snake_case` identifier boundary and types are limited to the proposal engine's
allow-list: `text`, `boolean`, `date`, `bigint`, and `numeric`.

## Privacy and authority boundary

The builder receives a `SchemaProposal` and a steward-provided `catalog_name`.
The proposal contains no raw source headers or sample values at this boundary.
The catalog name is used only to generate a safe table identifier. The builder
emits normalized target names, allow-listed types, nullability, proposal
identity, and source hashes.
It deliberately emits no DBML comments, notes, defaults, indexes, records,
relationship definitions, or example data.

`catalog_name` is steward-provided metadata and is normalized into a safe table
identifier. The connector performs no HTTP request, authentication, database
operation, file write, LLM call, or approval decision. A caller-owned adapter
must authenticate and authorize the request before sending it to pg-erd-cloud.
The upstream route is a design-first DBML-to-snapshot conversion boundary; this
slice does not persist a diagram or claim remote acceptance.

## Evidence and limits

- `tests/test_pg_erd_connector.py` checks all supported type mappings,
  nullability, deterministic serialization, empty proposals, unsafe inputs,
  and absence of protected values and DBML data blocks.
- The connector remains standalone and optional. Removing pg-erd-cloud does
  not change parsing, schema inference, PostgreSQL loading, or Semantic Data
  Portal operation.
- Relationships and multi-table lineage visualization require a later proposal
  contract that carries reviewed relationship evidence; inventing relationships
  from column names is intentionally out of scope.

The governing decision is [ADR-0019](adr/0019-pg-erd-visualization-handoff.md).
The DBML syntax baseline is recorded in the [research traceability matrix](RESEARCH_TRACEABILITY.md)
and [APA 7th reference list](doctoring/REFERENCES.md).
