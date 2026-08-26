"""HTML table extraction from MHTML HTML parts (stdlib only, no JS execution)."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Sequence


class TableExtractError(ValueError):
    """Fail-closed error when no usable table can be extracted."""


_SUPPRESSED_CONTAINER_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "object",
}

_IGNORED_VOID_RESOURCE_TAGS = {"embed"}

# Chunk size for incremental HTMLParser.feed (memory-bounded incremental parse).
_FEED_CHUNK = 256 * 1024


@dataclass(frozen=True)
class ExtractedTable:
    """Normalized top-level table with source headers and data rows."""

    headers: list[str]
    rows: list[list[str]]

    @property
    def column_count(self) -> int:
        """Return the number of normalized header columns."""
        return len(self.headers)

    @property
    def row_count(self) -> int:
        """Return the number of retained data rows."""
        return len(self.rows)


class _TopLevelTableParser(HTMLParser):
    """Extract top-level tables only; nested tables contribute text to parent cells."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._in_tr = False
        self._in_td = False
        self._cur_table: list[list[str]] | None = None
        self._cur_row: list[str] | None = None
        self._cur_cell: list[str] = []
        self._cell_attrs: dict[str, str] = {}
        self._suppression_stack: list[str] = []
        self._recover_unclosed_external_cdata = False

    def set_cdata_mode(self, elem: str, *, escapable: bool = False) -> None:
        """Keep script/style payload opaque while preserving malformed-head recovery."""
        del escapable
        self._recover_unclosed_external_cdata = self._table_depth < 1
        # Python 3.11.0 exposes set_cdata_mode(self, elem) without the newer
        # keyword parameter, so use the common positional contract across all
        # Python versions declared by this package.
        super().set_cdata_mode(elem)

    def clear_cdata_mode(self) -> None:
        """Clear stdlib raw-text mode and its document-recovery marker."""
        super().clear_cdata_mode()
        self._recover_unclosed_external_cdata = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if self._suppression_stack:
            if normalized in _SUPPRESSED_CONTAINER_TAGS:
                self._suppression_stack.append(normalized)
            return
        if normalized in _SUPPRESSED_CONTAINER_TAGS:
            # Closed script/style payloads outside a table remain opaque through
            # HTMLParser's raw-text mode. A missing document-level closer is
            # recovered only after the final feed so malformed head chrome does
            # not deny extraction of a later valid table. Once a table is open,
            # suppress the complete active-content subtree so markup cannot
            # create fake rows, cells, or nested tables.
            if self._table_depth >= 1:
                self._suppression_stack.append(normalized)
            return
        if normalized in _IGNORED_VOID_RESOURCE_TAGS:
            return

        ad = {k: (v or "") for k, v in attrs}
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._cur_table = []
            return
        if self._table_depth < 1:
            return
        if self._table_depth > 1:
            if self._in_td and tag == "br":
                self._cur_cell.append("\n")
            return
        if tag == "tr":
            self._in_tr = True
            self._cur_row = []
        elif tag in ("td", "th") and self._in_tr:
            self._in_td = True
            self._cur_cell = []
            self._cell_attrs = ad
        elif tag == "br" and self._in_td:
            self._cur_cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if self._suppression_stack:
            if normalized not in _SUPPRESSED_CONTAINER_TAGS:
                return
            expected = self._suppression_stack[-1]
            if normalized != expected:
                # A stray closer must not pop the still-open outer boundary or
                # expose text that remains inside it. Tolerate the malformed
                # closer and wait for the matching container end tag.
                return
            self._suppression_stack.pop()
            return
        if tag == "table":
            if self._table_depth == 1 and self._cur_table is not None:
                self.tables.append(self._cur_table)
                self._cur_table = None
            self._table_depth = max(0, self._table_depth - 1)
            return
        if self._table_depth != 1:
            return
        if tag in ("td", "th") and self._in_td:
            text = "".join(self._cur_cell).strip()
            x_str = self._cell_attrs.get("x:str")
            if text:
                val = text
            elif x_str is not None:
                val = x_str
            else:
                val = ""
            if self._cur_row is None:
                raise TableExtractError("table cell closed without an open row")
            # Expand colspan so header/data column counts stay aligned.
            span = 1
            raw_span = self._cell_attrs.get("colspan") or self._cell_attrs.get("COLSPAN")
            if raw_span:
                try:
                    span = max(1, int(str(raw_span).strip()))
                except ValueError as exc:
                    raise TableExtractError(f"invalid colspan={raw_span!r}") from exc
                if span > 100000:
                    raise TableExtractError(f"colspan too large: {span}")
            for _ in range(span):
                self._cur_row.append(val)
            self._in_td = False
            self._cur_cell = []
        elif tag == "tr" and self._in_tr:
            if self._cur_row is not None and self._cur_table is not None:
                self._cur_table.append(self._cur_row)
            self._in_tr = False
            self._cur_row = None

    def handle_data(self, data: str) -> None:
        if self._in_td and self._table_depth >= 1 and not self._suppression_stack:
            self._cur_cell.append(data)


def _feed_parser_chunked(parser: _TopLevelTableParser, text: str) -> None:
    """Feed HTML to the parser in chunks to bound intermediate parser buffer growth."""
    n = len(text)
    if n <= _FEED_CHUNK:
        parser.feed(text)
    else:
        for i in range(0, n, _FEED_CHUNK):
            parser.feed(text[i : i + _FEED_CHUNK])
    # A closed document-level script/style has already left CDATA mode and its
    # payload was never tokenized. If the closer is missing, clear raw-text mode
    # only after the final feed, then let HTMLParser recover later table markup.
    if parser.cdata_elem is not None and parser._recover_unclosed_external_cdata:
        parser.clear_cdata_mode()
    parser.close()
    if parser._suppression_stack:
        raise TableExtractError("unclosed suppression container")


def extract_tables_from_html(html: str | bytes) -> list[ExtractedTable]:
    """Parse HTML string/bytes and return extracted top-level tables.

    Accepts bytes (decoded once to str) or str. Feeds the parser incrementally
    so large worksheets are not re-copied into many intermediate full strings.
    """
    if isinstance(html, bytes):
        text = html.decode("utf-8", errors="replace")
    else:
        text = html
    if not text or not text.strip():
        raise TableExtractError("empty HTML input")

    parser = _TopLevelTableParser()
    _feed_parser_chunked(parser, text)
    # Allow GC of the full HTML string after parse by not retaining `text` beyond this.

    results: list[ExtractedTable] = []
    for raw in parser.tables:
        if not raw:
            continue
        headers = [str(c).strip() for c in raw[0]]
        if not any(headers):
            continue
        norm_headers: list[str] = []
        for i, h in enumerate(headers):
            norm_headers.append(h if h else f"col_{i + 1}")
        rows: list[list[str]] = []
        for raw_row in raw[1:]:
            # Preserve raw cell counts — do NOT pad/truncate. Validation rejects
            # inconsistent shapes fail-closed before load.
            cells = [str(c) for c in raw_row]
            if not any(c.strip() for c in cells):
                continue
            rows.append(cells)
        results.append(ExtractedTable(headers=norm_headers, rows=rows))
    return results


def extract_primary_table(html: str | bytes) -> ExtractedTable:
    """Return the largest usable table or fail closed."""
    tables = extract_tables_from_html(html)
    if not tables:
        raise TableExtractError("no HTML tables found")
    best = max(tables, key=lambda t: t.column_count * max(t.row_count, 1))
    if not best.headers:
        raise TableExtractError("primary table has no headers")
    return best


def rows_as_dicts(table: ExtractedTable) -> list[dict[str, str]]:
    """Zip headers to row values as ordered dict-like mappings."""
    out: list[dict[str, str]] = []
    for row in table.rows:
        out.append({h: row[i] if i < len(row) else "" for i, h in enumerate(table.headers)})
    return out


def assert_headers_present(table: ExtractedTable, required: Sequence[str]) -> None:
    """Raise when any required source header is absent from ``table``."""
    missing = [h for h in required if h not in table.headers]
    if missing:
        raise TableExtractError(f"missing required headers: {missing}")
