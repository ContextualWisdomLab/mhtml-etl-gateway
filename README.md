# MHTML ETL Gateway

Enterprise MHTML ingestion gateway that converts browser, SAP ALV, and Excel Web Archive exports into governed PostgreSQL data assets.

## Product Principles

- Immutable raw artifact preservation
- Deterministic MIME/HTML parsing
- Schema inference with validation gates
- PostgreSQL governed loading
- Full lineage and audit evidence
- No active HTML execution

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+ and (for live loads) PostgreSQL reachable via a connection URI.

## Quick start

### Dry-run (parse + type map + DDL, no database)

```bash
mhtml-etl-gateway path/to/export.MHTML --dry-run --ddl-out /tmp/schema.sql --lineage-json /tmp/lineage.json
```

### Load into PostgreSQL

```bash
export MHTML_ETL_DSN="postgresql://user:pass@localhost:5432/dbname"
# or: export DATABASE_URL=...

mhtml-etl-gateway path/to/ZCRHT811_export_20260220_20260301.MHTML \
  --table-name zcrht811_export_rows \
  --lineage-json ./lineage.json \
  --json
```

Environment variables:

| Variable | Purpose |
|----------|---------|
| `MHTML_ETL_DSN` | Preferred PostgreSQL connection URI |
| `DATABASE_URL` | Fallback connection URI |

### Python API

```python
from mhtml_etl_gateway import convert_mhtml_to_postgres, extract_table

# Headers + rows only
table = extract_table("export.MHTML")
assert "MANDT" in table.headers

# Full load
result = convert_mhtml_to_postgres(
    "export.MHTML",
    dsn="postgresql:///mhtml_etl",
    table_name="zcrht811_export_rows",
)
print(result["inserted_rows"], result["ddl"])
```

## Pipeline stages

1. **MIME parser** — multipart extraction; never executes scripts; never fetches external resources
2. **HTML table extractor** — top-level table only (nested cell HTML stays cell text)
3. **Schema inference** — PostgreSQL types + multiword `snake_case` object names
4. **PostgreSQL loader** — `CREATE TABLE IF NOT EXISTS` + insert with lineage columns:
   - `source_artifact_path`
   - `source_artifact_sha256`
   - `source_row_number`
   - `loaded_at`

## Tests

```bash
export MHTML_ETL_DSN="postgresql:///mhtml_etl"   # optional live-DB test
# Optional: point at a local real export (do not commit this path)
# export MHTML_ETL_REAL_SAMPLE="/path/to/ZCRHT811_export_….MHTML"
pytest -v
```

Fixture: `tests/fixtures/zcrht811_sample.MHTML` (SAP ALV–shaped multipart HTML).  
Real CRM paths stay on the operator machine via `MHTML_ETL_REAL_SAMPLE` — never committed.

## Current Status

Implemented MHTML → tabular extract → PostgreSQL type map → load path for SAP ALV Excel Web Archive `.MHTML` (e.g. `ZCRHT811_export_*.MHTML`).
