"""Immutable contracts shared by parsing, inspection, and future loading layers."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any


@dataclass(frozen=True, slots=True)
class ParseLimits:
    """Resource budgets applied before and during untrusted document parsing."""

    max_source_bytes: int = 250 * 1024 * 1024
    max_mime_parts: int = 256
    max_html_chars: int = 50_000_000
    max_tables: int = 128
    max_rows_per_table: int = 1_000_000
    max_columns_per_table: int = 4096
    max_total_cells: int = 10_000_000
    max_cell_text_chars: int = 1_000_000

    def __post_init__(self) -> None:
        """Reject non-positive or boolean resource budgets."""
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field.name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Non-fatal condition preserved in an inspection report."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-ready diagnostic representation."""
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class MhtmlDocument:
    """Decoded root HTML selected from an immutable MHTML source."""

    html_text: str
    root_content_type: str
    root_content_location: str | None
    root_content_id: str | None
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class TableCell:
    """One logical cell after rowspan and colspan expansion."""

    text: str
    is_header: bool


@dataclass(frozen=True, slots=True)
class ExtractedTable:
    """Rectangular normalized table extracted without rendering HTML."""

    table_index: int
    rows: tuple[tuple[TableCell, ...], ...]
    header_row_index: int | None
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        """Validate rectangular shape and header coordinates."""
        widths = {len(row) for row in self.rows}
        if len(widths) > 1:
            raise ValueError("ExtractedTable rows must be rectangular")
        if self.header_row_index is not None and not (
            0 <= self.header_row_index < len(self.rows)
        ):
            raise ValueError("header_row_index must identify an existing row")

    @property
    def row_count(self) -> int:
        """Return the normalized number of rows including the header row."""
        return len(self.rows)

    @property
    def data_row_count(self) -> int:
        """Return rows other than the selected header row."""
        return self.row_count - (1 if self.header_row_index is not None else 0)

    @property
    def column_count(self) -> int:
        """Return the normalized logical width of the table."""
        return len(self.rows[0]) if self.rows else 0

    @property
    def headers(self) -> tuple[str, ...]:
        """Return text from the selected header row, or an empty tuple."""
        if self.header_row_index is None:
            return ()
        return tuple(cell.text for cell in self.rows[self.header_row_index])

    @property
    def header_source(self) -> str:
        """Return ``semantic``, ``positional``, or ``none`` for the header row."""
        if self.header_row_index is None:
            return "none"
        if any(cell.is_header for cell in self.rows[self.header_row_index]):
            return "semantic"
        return "positional"


@dataclass(frozen=True, slots=True)
class TableInspection:
    """Metadata-only summary of one extracted table."""

    table_index: int
    row_count: int
    data_row_count: int
    column_count: int
    header_row_index: int | None
    header_source: str
    header_value_count: int
    header_values_included: bool
    headers: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready structure that intentionally excludes row values."""
        return {
            "table_index": self.table_index,
            "row_count": self.row_count,
            "data_row_count": self.data_row_count,
            "column_count": self.column_count,
            "header_row_index": self.header_row_index,
            "header_source": self.header_source,
            "header_value_count": self.header_value_count,
            "header_values_included": self.header_values_included,
            "headers": list(self.headers),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass(frozen=True, slots=True)
class InspectionReport:
    """Metadata-only lineage report for one immutable MHTML source."""

    source_hash_sha256: str
    source_size_bytes: int
    root_content_type: str
    root_content_location_scheme: str | None
    root_content_location_hash_sha256: str | None
    diagnostics: tuple[Diagnostic, ...]
    tables: tuple[TableInspection, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the stable public report representation."""
        return {
            "source_hash_sha256": self.source_hash_sha256,
            "source_size_bytes": self.source_size_bytes,
            "root_content_type": self.root_content_type,
            "root_content_location_scheme": self.root_content_location_scheme,
            "root_content_location_hash_sha256": self.root_content_location_hash_sha256,
            "table_count": len(self.tables),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "tables": [table.to_dict() for table in self.tables],
        }
