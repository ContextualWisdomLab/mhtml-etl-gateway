"""Metadata-only MHTML inspection and source-lineage assembly."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import ErrorCode, MhtmlGatewayError
from .html_tables import extract_tables
from .mime_parser import parse_mhtml_bytes
from .models import InspectionReport, ParseLimits, TableInspection


def _content_location_hash(location: str | None) -> str | None:
    """Return an exact hash for an optional source-controlled location."""
    if location is None:
        return None
    return hashlib.sha256(location.encode("utf-8")).hexdigest()


def inspect_mhtml_bytes(
    source_bytes: bytes,
    *,
    limits: ParseLimits | None = None,
) -> InspectionReport:
    """Inspect source bytes while excluding every cell-derived value."""
    document = parse_mhtml_bytes(source_bytes, limits=limits)
    tables = extract_tables(document, limits=limits)
    table_summaries = tuple(
        TableInspection(
            row_count=table.row_count,
            data_row_count=table.data_row_count,
            column_count=table.column_count,
            header_row_index=table.header_row_index,
            header_source=table.header_source,
            header_value_count=len(table.headers),
            diagnostics=table.diagnostics,
        )
        for table in tables
    )
    return InspectionReport(
        source_hash_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_size_bytes=len(source_bytes),
        root_content_location_hash_sha256=_content_location_hash(
            document.root_content_location
        ),
        diagnostics=document.diagnostics,
        tables=table_summaries,
    )


def inspect_mhtml_file(
    source_path: str | Path,
    *,
    limits: ParseLimits | None = None,
) -> InspectionReport:
    """Read a source file once and produce its value-free inspection report."""
    path = Path(source_path)
    try:
        source_bytes = path.read_bytes()
    except OSError as exc:
        raise MhtmlGatewayError(ErrorCode.SOURCE_READ_FAILED) from exc
    return inspect_mhtml_bytes(source_bytes, limits=limits)
