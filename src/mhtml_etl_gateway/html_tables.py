"""Non-rendering, bounded HTML table extraction and span normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re

from .errors import ErrorCode, MhtmlGatewayError
from .models import Diagnostic, ExtractedTable, MhtmlDocument, ParseLimits, TableCell

_SUPPRESSED_CONTAINER_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "object",
}
_IGNORED_VOID_RESOURCE_TAGS = {"embed"}
_BLOCK_BREAK_TAGS = {"div", "p", "li"}
_WHITESPACE_RUN = re.compile(r"[\t\f\v ]+")
_NEWLINE_PADDING = re.compile(r" *\n *")
_EXTRA_NEWLINES = re.compile(r"\n{3,}")


@dataclass(slots=True)
class _RawCell:
    """Mutable cell collected directly from HTML parser callbacks."""

    is_header: bool
    rowspan: int
    colspan: int
    fragments: list[str] = field(default_factory=list)
    character_count: int = 0


@dataclass(slots=True)
class _RawTable:
    """Mutable table preserving source rows before span expansion."""

    rows: list[list[_RawCell]] = field(default_factory=list)


class _TableParser(HTMLParser):
    """Collect table structure without rendering or resolving resources."""

    def __init__(self, limits: ParseLimits) -> None:
        """Initialize parser state and document-wide budgets."""
        super().__init__(convert_charrefs=True)
        self.limits = limits
        self.tables: list[_RawTable] = []
        self._current_table: _RawTable | None = None
        self._current_row: list[_RawCell] | None = None
        self._current_cell: _RawCell | None = None
        self._table_depth = 0
        self._suppression_stack: list[str] = []

    @staticmethod
    def _span_value(
        attributes: list[tuple[str, str | None]],
        name: str,
    ) -> int:
        """Parse a positive rowspan or colspan attribute."""
        raw = next(
            (value for key, value in attributes if key.lower() == name),
            None,
        )
        if raw is None:
            return 1
        try:
            value = int(raw, 10)
        except (TypeError, ValueError) as exc:
            raise MhtmlGatewayError(ErrorCode.INVALID_TABLE_SPAN) from exc
        if value <= 0:
            raise MhtmlGatewayError(ErrorCode.INVALID_TABLE_SPAN)
        return value

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Update structural state for one opening HTML tag."""
        normalized = tag.lower()
        if self._suppression_stack:
            if normalized in _SUPPRESSED_CONTAINER_TAGS:
                self._suppression_stack.append(normalized)
            return
        if normalized in _SUPPRESSED_CONTAINER_TAGS:
            self._suppression_stack.append(normalized)
            return
        if normalized in _IGNORED_VOID_RESOURCE_TAGS:
            return
        if normalized == "table":
            self._table_depth += 1
            if self._table_depth > 1:
                raise MhtmlGatewayError(ErrorCode.NESTED_TABLE)
            if len(self.tables) >= self.limits.max_tables:
                raise MhtmlGatewayError(ErrorCode.TOO_MANY_TABLES)
            self._current_table = _RawTable()
            self.tables.append(self._current_table)
            return
        if self._table_depth != 1 or self._suppression_stack:
            return
        if normalized == "tr":
            if (
                len(self._current_table.rows)
                >= self.limits.max_rows_per_table
            ):  # type: ignore[union-attr]
                raise MhtmlGatewayError(ErrorCode.TOO_MANY_ROWS)
            self._current_row = []
            self._current_table.rows.append(  # type: ignore[union-attr]
                self._current_row
            )
            return
        if normalized in {"td", "th"} and self._current_row is not None:
            self._current_cell = _RawCell(
                is_header=normalized == "th",
                rowspan=self._span_value(attrs, "rowspan"),
                colspan=self._span_value(attrs, "colspan"),
            )
            self._current_row.append(self._current_cell)
            return
        if self._current_cell is not None:
            if normalized == "br":
                self._append_fragment("\n")
            elif normalized in _BLOCK_BREAK_TAGS:
                self._append_fragment(" ")

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Process self-closing tags without reading resource attributes."""
        del attrs
        normalized = tag.lower()
        if (
            normalized == "br"
            and self._current_cell is not None
            and not self._suppression_stack
        ):
            self._append_fragment("\n")

    def handle_endtag(self, tag: str) -> None:
        """Update structural state for one closing HTML tag."""
        normalized = tag.lower()
        if self._suppression_stack:
            if normalized == self._suppression_stack[-1]:
                self._suppression_stack.pop()
            return
        if normalized == "table":
            self._table_depth = 0
            self._current_table = None
            self._current_row = None
            self._current_cell = None
            return
        if self._table_depth != 1 or self._suppression_stack:
            return
        if normalized in {"td", "th"}:
            self._current_cell = None
        elif normalized == "tr":
            self._current_row = None
        elif (
            normalized in _BLOCK_BREAK_TAGS
            and self._current_cell is not None
        ):
            self._append_fragment(" ")

    def handle_data(self, data: str) -> None:
        """Collect visible character data only while inside a table cell."""
        if self._current_cell is not None and not self._suppression_stack:
            self._append_fragment(data)

    def _append_fragment(self, fragment: str) -> None:
        """Append bounded text to the active source cell."""
        current_cell = self._current_cell
        current_cell.character_count += len(fragment)  # type: ignore[union-attr]
        if (
            current_cell.character_count  # type: ignore[union-attr]
            > self.limits.max_cell_text_chars
        ):
            raise MhtmlGatewayError(ErrorCode.CELL_TEXT_TOO_LARGE)
        current_cell.fragments.append(fragment)  # type: ignore[union-attr]


def _normalize_text(fragments: list[str]) -> str:
    """Normalize cell whitespace while preserving explicit line breaks."""
    text = "".join(fragments).replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        normalized = _WHITESPACE_RUN.sub(" ", line).strip()
        lines.append(normalized)
    compact = "\n".join(lines)
    compact = _NEWLINE_PADDING.sub("\n", compact)
    compact = _EXTRA_NEWLINES.sub("\n\n", compact)
    return compact.strip(" \n")


def _project_table_shape(
    raw_table: _RawTable,
    limits: ParseLimits,
    total_cells_so_far: int,
) -> tuple[int, int]:
    """Validate span geometry and return final rows and width before allocation."""
    pending: dict[int, int] = {}
    processed_rows = 0
    max_width = 0

    def reject_oversized_projection() -> None:
        trailing_rows = max(pending.values(), default=0)
        projected_rows = processed_rows + trailing_rows
        pending_width = max(pending, default=-1) + 1
        projected_width = max(max_width, pending_width)
        if (
            total_cells_so_far + projected_rows * projected_width
            > limits.max_total_cells
        ):
            raise MhtmlGatewayError(ErrorCode.TOO_MANY_CELLS)

    for source_row in raw_table.rows:
        column = 0

        def consume_pending_until_free() -> None:
            nonlocal column
            while column in pending:
                remaining = pending[column]
                if remaining <= 1:
                    del pending[column]
                else:
                    pending[column] = remaining - 1
                column += 1

        consume_pending_until_free()
        for raw_cell in source_row:
            consume_pending_until_free()
            if processed_rows + raw_cell.rowspan > limits.max_rows_per_table:
                raise MhtmlGatewayError(ErrorCode.TOO_MANY_ROWS)
            for _ in range(raw_cell.colspan):
                if column in pending:
                    raise MhtmlGatewayError(ErrorCode.INVALID_TABLE_SPAN)
                if column >= limits.max_columns_per_table:
                    raise MhtmlGatewayError(ErrorCode.TOO_MANY_COLUMNS)
                if raw_cell.rowspan > 1:
                    pending[column] = raw_cell.rowspan - 1
                column += 1
            consume_pending_until_free()

        while pending and column <= max(pending):
            if column in pending:
                remaining = pending[column]
                if remaining <= 1:
                    del pending[column]
                else:
                    pending[column] = remaining - 1
            column += 1
        processed_rows += 1
        max_width = max(max_width, column)
        reject_oversized_projection()

    trailing_rows = max(pending.values(), default=0)
    final_rows = processed_rows + trailing_rows
    final_width = max(max_width, max(pending, default=-1) + 1)
    return final_rows, final_width


def _expand_table(
    raw_table: _RawTable,
    limits: ParseLimits,
    total_cells_so_far: int,
) -> tuple[ExtractedTable, int]:
    """Expand spans, pad rows, infer headers, and return total cell usage."""
    projected_rows, projected_width = _project_table_shape(
        raw_table,
        limits,
        total_cells_so_far,
    )
    normalized_rows: list[list[TableCell]] = []
    pending: dict[int, tuple[int, TableCell]] = {}
    max_width = 0

    for source_row in raw_table.rows:
        row: list[TableCell] = []
        column = 0

        def fill_pending_until_free() -> None:
            nonlocal column
            while column in pending:
                remaining, pending_cell = pending[column]
                row.append(pending_cell)
                if remaining <= 1:
                    del pending[column]
                else:
                    pending[column] = (remaining - 1, pending_cell)
                column += 1

        fill_pending_until_free()
        for raw_cell in source_row:
            fill_pending_until_free()
            cell = TableCell(
                _normalize_text(raw_cell.fragments),
                raw_cell.is_header,
            )
            for _ in range(raw_cell.colspan):
                row.append(cell)
                if raw_cell.rowspan > 1:
                    pending[column] = (raw_cell.rowspan - 1, cell)
                column += 1
            fill_pending_until_free()

        while pending and column <= max(pending):
            if column in pending:
                remaining, pending_cell = pending[column]
                row.append(pending_cell)
                if remaining <= 1:
                    del pending[column]
                else:
                    pending[column] = (remaining - 1, pending_cell)
            else:
                row.append(TableCell("", False))
            column += 1
        max_width = max(max_width, len(row))
        normalized_rows.append(row)

    while pending:
        row = []
        highest = max(pending)
        for column in range(highest + 1):
            if column in pending:
                remaining, pending_cell = pending[column]
                row.append(pending_cell)
                if remaining <= 1:
                    del pending[column]
                else:
                    pending[column] = (remaining - 1, pending_cell)
            else:
                row.append(TableCell("", False))
        max_width = max(max_width, len(row))
        normalized_rows.append(row)

    for row in normalized_rows:
        row.extend(
            TableCell("", False) for _ in range(max_width - len(row))
        )

    normalized_cell_count = len(normalized_rows) * max_width
    if len(normalized_rows) != projected_rows or max_width != projected_width:
        raise MhtmlGatewayError(ErrorCode.INVALID_TABLE_SPAN)
    new_total = total_cells_so_far + normalized_cell_count

    header_index = next(
        (
            index
            for index, row in enumerate(normalized_rows)
            if any(cell.text for cell in row)
        ),
        None,
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    if header_index is not None and not any(
        cell.is_header for cell in normalized_rows[header_index]
    ):
        diagnostics = (
            Diagnostic(
                "positional_header",
                "The first non-empty row was inferred as a header because it contained no th elements",
            ),
        )

    table = ExtractedTable(
        rows=tuple(tuple(row) for row in normalized_rows),
        header_row_index=header_index,
        diagnostics=diagnostics,
    )
    return table, new_total


def extract_tables(
    document: MhtmlDocument,
    *,
    limits: ParseLimits | None = None,
) -> tuple[ExtractedTable, ...]:
    """Extract bounded top-level tables from decoded HTML without rendering."""
    effective_limits = limits or ParseLimits()
    if len(document.html_text) > effective_limits.max_html_chars:
        raise MhtmlGatewayError(ErrorCode.HTML_TOO_LARGE)
    parser = _TableParser(effective_limits)
    parser.feed(document.html_text)
    parser.close()

    tables: list[ExtractedTable] = []
    total_cells = 0
    for raw_table in parser.tables:
        table, total_cells = _expand_table(
            raw_table,
            effective_limits,
            total_cells,
        )
        tables.append(table)
    return tuple(tables)
