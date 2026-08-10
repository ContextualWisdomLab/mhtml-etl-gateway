# MHTML ETL Gateway

Enterprise MHTML ingestion gateway that converts browser, SAP ALV, and Excel Web Archive exports into governed PostgreSQL data assets.

## Product Principles

- Immutable raw artifact preservation
- Deterministic MIME/HTML parsing (no script execution, no external fetch)
- Fail-closed validation before load
- Schema inference with multiword `snake_case` DB names
- Idempotent PostgreSQL loading (content sha256 + ingest catalog)
- Full lineage on every row
- Operator paths only via CLI/env — **never commit real CRM absolute paths**

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+; PostgreSQL for live loads.

## Environment

| Variable | Purpose |
|----------|---------|
| `MHTML_ETL_DSN` | Preferred PostgreSQL URI |
| `DATABASE_URL` | Fallback PostgreSQL URI |
| `MHTML_ETL_SOURCE_DIR` | Directory of `.MHTML` files for `batch` (operator machine only) |
| `MHTML_ETL_REAL_SAMPLE` | Optional single real file for local optional tests |

## Single-file load

```bash
export MHTML_ETL_DSN="postgresql://user:pass@localhost:5432/dbname"

mhtml-etl-gateway load path/to/export.MHTML \
  --table-name zcrht811_export_rows \
  --on-duplicate skip \
  --json
```

Idempotency:

- `--on-duplicate skip` (default): second load of the same sha256 does **not** grow row count
- `--on-duplicate replace`: delete rows for that sha256, then re-insert

Dry-run (parse + validate + type map, in-memory sink):

```bash
mhtml-etl-gateway load path/to/export.MHTML --dry-run --ddl-out schema.sql
```

## Batch directory load

```bash
export MHTML_ETL_DSN="postgresql:///mhtml_etl"
export MHTML_ETL_SOURCE_DIR="/path/on/your/machine/to/crm-mhtml"   # local only

mhtml-etl-gateway batch \
  --table-name zcrht811_export_rows \
  --on-duplicate skip \
  --limit 3 \
  --json
```

Or pass the directory as a positional argument (still not committed to git):

```bash
mhtml-etl-gateway batch "$MHTML_ETL_SOURCE_DIR" --dsn "$MHTML_ETL_DSN" --json
```

## Validation

Before load, the gateway requires non-empty headers, consistent row widths, and ≥1 data row.
ZCRHT811-shaped tables (headers include `MANDT` + `GUID`, or table name contains `zcrht811`)
require **`MANDT`** and **`GUID`**. Override with:

```bash
mhtml-etl-gateway load file.MHTML --required-headers MANDT,GUID
mhtml-etl-gateway load file.MHTML --required-headers none   # disable extra requirements
```

## Ingest catalog

Table `mhtml_ingest_artifact` records `(source_artifact_sha256, table_name)` with path, size, row_count, status, loaded_at.

## Docker (optional)

```bash
docker build -t mhtml-etl-gateway .
docker run --rm -e MHTML_ETL_DSN -v "$PWD/data:/data:ro" mhtml-etl-gateway \
  load /data/export.MHTML --json
```

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tests

```bash
pytest -v
# optional live PG:
export MHTML_ETL_DSN="postgresql:///mhtml_etl"
pytest -v
```

Fixture: `tests/fixtures/zcrht811_sample.MHTML`.

## Version

0.2.0 — production-capable validation, batch, idempotent catalog load, CI.
