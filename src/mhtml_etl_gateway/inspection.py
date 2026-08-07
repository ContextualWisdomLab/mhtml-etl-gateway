"""Metadata-only MHTML inspection and source-lineage assembly."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from .errors import ErrorCode, MhtmlGatewayError
from .html_tables import extract_tables
from .mime_parser import parse_mhtml_bytes
from .models import InspectionReport, ParseLimits, TableInspection



def _content_location_metadata(location: str | None) -> tuple[str | None, str | None]:
    """Return a non-sensitive scheme and exact hash for an optional location."""
    if location is None:
        return None, None
    try:
        scheme = urlsplit(location).scheme.lower() or "relative"
    except ValueError:
        scheme = "invalid"
    return scheme, hashlib.sha256(location.encode("utf-8")).hexdigest()

def inspect_mhtml_bytes(
    source_bytes: bytes,
    *,
    limits: ParseLimits | None = None,
    include_header_values: bool = False,
) -> InspectionReport:
    """Inspect source bytes, excluding all cell values unless explicitly requested."""
    if not isinstance(include_header_values, bool):
        raise ValueError("include_header_values must be a boolean")
    document = parse_mhtml_bytes(source_bytes, limits=limits)
    tables = extract_tables(document, limits=limits)
    table_summaries = tuple(
        TableInspection(
            table_index=table.table_index,
            row_count=table.row_count,
            data_row_count=table.data_row_count,
            column_count=table.column_count,
            header_row_index=table.header_row_index,
            header_source=table.header_source,
            header_value_count=len(table.headers),
            header_values_included=include_header_values and bool(table.headers),
            headers=table.headers if include_header_values else (),
            diagnostics=table.diagnostics,
        )
        for table in tables
    )
    location_scheme, location_hash = _content_location_metadata(
        document.root_content_location
    )
    return InspectionReport(
        source_hash_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_size_bytes=len(source_bytes),
        root_content_type=document.root_content_type,
        root_content_location_scheme=location_scheme,
        root_content_location_hash_sha256=location_hash,
        diagnostics=document.diagnostics,
        tables=table_summaries,
    )


def inspect_mhtml_file(
    source_path: str | Path,
    *,
    limits: ParseLimits | None = None,
    include_header_values: bool = False,
) -> InspectionReport:
    """Read a source file once and produce its metadata-only inspection report."""
    path = Path(source_path)
    try:
        source_bytes = path.read_bytes()
    except OSError as exc:
        raise MhtmlGatewayError(
            ErrorCode.SOURCE_READ_FAILED,
            "Could not read MHTML source",
        ) from exc
    return inspect_mhtml_bytes(
        source_bytes,
        limits=limits,
        include_header_values=include_header_values,
    )
