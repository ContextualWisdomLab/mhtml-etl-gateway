"""End-to-end MHTML → validate → type → PostgreSQL pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from mhtml_etl_gateway.html_table_extractor import (
    ExtractedTable,
    extract_primary_table,
)
from mhtml_etl_gateway.column_mapping import (
    ColumnMappingReport,
    attach_column_comments,
    load_column_mapping,
)
from mhtml_etl_gateway.lineage import (
    artifact_reference,
    build_lineage,
    sha256_bytes,
    write_lineage_json,
)
from mhtml_etl_gateway.mhtml_parser import extract_html_bytes, read_mhtml_file
from mhtml_etl_gateway.postgres_loader import (
    InMemorySink,
    LoadResult,
    OnDuplicate,
    PsycopgSink,
    RowSink,
    load_table,
)
from mhtml_etl_gateway.schema_inference import TableSchema, infer_table_schema
from mhtml_etl_gateway.validation_engine import validate_extracted_table


@dataclass(frozen=True)
class ExtractResult:
    headers: list[str]
    rows: list[list[str]]
    table: ExtractedTable
    source_path: str
    source_sha256: str
    source_size: int


def _default_table_name(path: Path) -> str:
    # Never derive a database object name from an operator-provided filename.
    # Callers can still provide an explicit, safe --table-name.
    del path
    return "mhtml_extracted_rows"


def extract_table(path: str | Path, *, data: bytes | None = None) -> ExtractResult:
    """Parse MHTML file/bytes and return headers + data rows (no DB).

    Reads the file once when ``data`` is None; HTML part is sliced from that
    buffer (no second disk read).
    """
    p = Path(path)
    if data is None:
        data = read_mhtml_file(p)
    digest = sha256_bytes(data)
    html = extract_html_bytes(data)
    table = extract_primary_table(html)
    return ExtractResult(
        headers=list(table.headers),
        rows=[list(r) for r in table.rows],
        table=table,
        source_path=str(p),
        source_sha256=digest,
        source_size=len(data),
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
    column_mapping: str | Path | None = None,
    data: bytes | None = None,
    on_duplicate: OnDuplicate = "skip",
    required_headers: Sequence[str] | None = None,
    require_data_rows: bool = True,
) -> dict[str, Any]:
    """Full pipeline: parse → validate → type map → idempotent load.

    Provide either ``dsn`` (live PostgreSQL) or an injectable ``sink``.
    If neither is provided, uses InMemorySink (dry-run friendly).
    """
    p = Path(path)
    if data is None:
        data = read_mhtml_file(p)
    extracted = extract_table(p, data=data)
    schema = infer_schema_for_extract(extracted, table_name=table_name)
    artifact_ref = artifact_reference(extracted.source_sha256)
    mapping_report: ColumnMappingReport | None = None
    if column_mapping is not None:
        mapping_document = load_column_mapping(column_mapping)
        schema, mapping_report = attach_column_comments(schema, mapping_document)

    # Fail closed before any business-row write.
    validate_extracted_table(
        extracted.headers,
        extracted.rows,
        table_name=schema.table_name,
        required_headers=required_headers,
        require_data_rows=require_data_rows,
    )

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
            source_artifact_path=artifact_ref,
            source_artifact_sha256=extracted.source_sha256,
            source_artifact_size=extracted.source_size,
            on_duplicate=on_duplicate,
        )
        row_count_for_lineage = (
            int(result.catalog_entry.get("row_count", len(extracted.rows)))
            if result.skipped and result.catalog_entry
            else result.inserted_rows
        )
        lineage = build_lineage(
            p,
            data=data,
            row_count=row_count_for_lineage,
            table_name=result.table_name,
            source_artifact_path=artifact_ref,
        )
        lineage_dict = lineage.to_dict()
        if result.skipped:
            lineage_dict["skipped"] = True

        lineage_path = None
        if lineage_json:
            lineage_path = str(write_lineage_json(lineage, lineage_json))

        db_count = active.count_rows(result.table_name)
        queryable: dict[str, Any] = {
            "row_count": db_count,
            "table_name": result.table_name,
            "db_row_count": db_count,
        }
        if isinstance(active, PsycopgSink):
            sample = active.query_sample(result.table_name, limit=3)
            queryable["sample"] = [list(r) for r in sample]
        elif isinstance(active, InMemorySink):
            stored = active.rows.get(result.table_name, [])
            queryable["sample"] = stored[:3]

        return {
            "headers": extracted.headers,
            "data_row_count": len(extracted.rows),
            "inserted_rows": result.inserted_rows,
            "skipped": result.skipped,
            "replaced": result.replaced,
            "table_name": result.table_name,
            "schema": schema.type_map(),
            "column_comments": schema.comment_map(),
            "column_mapping": mapping_report.to_dict() if mapping_report else None,
            "ddl": result.ddl,
            "catalog": result.catalog_entry,
            "lineage": lineage_dict,
            "lineage_json": lineage_path,
            "queryable": queryable,
            "source_sha256": extracted.source_sha256,
            "on_duplicate": on_duplicate,
        }
    finally:
        if own_sink and isinstance(active, PsycopgSink):
            active.close()
