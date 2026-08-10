"""HTML table extraction from MHTML HTML parts (stdlib only, no JS execution)."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Sequence


class TableExtractError(ValueError):
    """Fail-closed error when no usable table can be extracted."""


# Chunk size for incremental HTMLParser.feed (memory-bounded incremental parse).
_FEED_CHUNK = 256 * 1024


@dataclass(frozen=True)
class ExtractedTable:
    headers: list[str]
    rows: list[list[str]]

    @property
    def column_count(self) -> int:
        return len(self.headers)

    @property
    def row_count(self) -> int:
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
            assert self._cur_row is not None
            self._cur_row.append(val)
            self._in_td = False
            self._cur_cell = []
        elif tag == "tr" and self._in_tr:
            if self._cur_row is not None and self._cur_table is not None:
                self._cur_table.append(self._cur_row)
            self._in_tr = False
            self._cur_row = None

    def handle_data(self, data: str) -> None:
        if self._in_td and self._table_depth >= 1:
            self._cur_cell.append(data)


def _feed_parser_chunked(parser: _TopLevelTableParser, text: str) -> None:
    """Feed HTML to the parser in chunks to bound intermediate parser buffer growth."""
    n = len(text)
    if n <= _FEED_CHUNK:
        parser.feed(text)
        parser.close()
        return
    for i in range(0, n, _FEED_CHUNK):
        parser.feed(text[i : i + _FEED_CHUNK])
    parser.close()


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
    missing = [h for h in required if h not in table.headers]
    if missing:
        raise TableExtractError(f"missing required headers: {missing}")
