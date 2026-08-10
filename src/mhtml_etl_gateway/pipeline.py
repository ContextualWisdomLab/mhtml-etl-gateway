"""End-to-end MHTML → extract → type → PostgreSQL pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mhtml_etl_gateway.html_table_extractor import (
    ExtractedTable,
    extract_primary_table,
)
from mhtml_etl_gateway.lineage import build_lineage, sha256_bytes, write_lineage_json
from mhtml_etl_gateway.mhtml_parser import extract_html_bytes
from mhtml_etl_gateway.postgres_loader import (
    InMemorySink,
    LoadResult,
    PsycopgSink,
    RowSink,
    load_table,
)
from mhtml_etl_gateway.schema_inference import TableSchema, infer_table_schema, to_snake_case


@dataclass(frozen=True)
class ExtractResult:
    headers: list[str]
    rows: list[list[str]]
    table: ExtractedTable
    source_path: str
    source_sha256: str


def _default_table_name(path: Path) -> str:
    stem = path.stem  # e.g. ZCRHT811_export_20260220_20260301
    # Prefer report id prefix when present.
    parts = stem.split("_")
    if parts:
        base = parts[0]
        if base.upper().startswith("Z") or base.isalnum():
            return to_snake_case(f"{base}_export_rows")
    return to_snake_case(f"{stem}_rows")


def extract_table(path: str | Path, *, data: bytes | None = None) -> ExtractResult:
    """Parse MHTML file/bytes and return headers + data rows (no DB)."""
    p = Path(path)
    if data is None:
        if not p.is_file():
            raise FileNotFoundError(f"MHTML file not found: {p}")
        data = p.read_bytes()
    digest = sha256_bytes(data)
    html = extract_html_bytes(data)
    table = extract_primary_table(html)
    return ExtractResult(
        headers=list(table.headers),
        rows=[list(r) for r in table.rows],
        table=table,
        source_path=str(p),
        source_sha256=digest,
    )


def infer_schema_for_extract(
    extracted: ExtractResult,
    *,
    table_name: str | None = None,
) -> TableSchema:
    name = table_name or _default_table_name(Path(extracted.source_path))
    return infer_table_schema(extracted.headers, extracted.rows, table_name=name)


def convert_mhtml_to_postgres(
    path: str | Path,
    *,
    dsn: str | None = None,
    sink: RowSink | None = None,
    table_name: str | None = None,
    lineage_json: str | Path | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    """Full pipeline: parse → extract → type map → load.

    Provide either ``dsn`` (live PostgreSQL) or an injectable ``sink``.
    If neither is provided, uses InMemorySink (dry-run friendly).
    """
    p = Path(path)
    if data is None:
        data = p.read_bytes()
    extracted = extract_table(p, data=data)
    schema = infer_schema_for_extract(extracted, table_name=table_name)

    own_sink = False
    active: RowSink
    if sink is not None:
        active = sink
    elif dsn:
        active = PsycopgSink(dsn)
        own_sink = True
    else:
        active = InMemorySink()

    try:
        result: LoadResult = load_table(
            schema,
            extracted.rows,
            sink=active,
            source_artifact_path=extracted.source_path,
            source_artifact_sha256=extracted.source_sha256,
        )
        lineage = build_lineage(
            p,
            data=data,
            row_count=result.inserted_rows,
            table_name=result.table_name,
        )
        lineage_path = None
        if lineage_json:
            lineage_path = str(write_lineage_json(lineage, lineage_json))

        queryable: dict[str, Any] = {
            "row_count": result.inserted_rows,
            "table_name": result.table_name,
        }
        if isinstance(active, PsycopgSink):
            queryable["db_row_count"] = active.query_count(result.table_name)
            sample = active.query_sample(result.table_name, limit=3)
            queryable["sample"] = [list(r) for r in sample]
        elif isinstance(active, InMemorySink):
            stored = active.rows.get(result.table_name, [])
            queryable["db_row_count"] = len(stored)
            queryable["sample"] = stored[:3]

        return {
            "headers": extracted.headers,
            "data_row_count": len(extracted.rows),
            "inserted_rows": result.inserted_rows,
            "table_name": result.table_name,
            "schema": schema.type_map(),
            "ddl": result.ddl,
            "lineage": lineage.to_dict(),
            "lineage_json": lineage_path,
            "queryable": queryable,
            "source_sha256": extracted.source_sha256,
        }
    finally:
        if own_sink and isinstance(active, PsycopgSink):
            active.close()
