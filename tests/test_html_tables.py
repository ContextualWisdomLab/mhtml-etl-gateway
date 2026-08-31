"""Tests for deterministic HTML table extraction."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.html_tables import extract_tables
from mhtml_etl_gateway.mime_parser import parse_mhtml_bytes
from mhtml_etl_gateway.models import ParseLimits
from tests.fixture_factory import make_mhtml


def extract(html: str, *, limits: ParseLimits | None = None):
    """Parse synthetic MHTML and return its extracted tables."""
    document = parse_mhtml_bytes(make_mhtml(html), limits=limits)
    return extract_tables(document, limits=limits)


class HtmlTableTests(unittest.TestCase):
    """Verify HTML normalization without active-content execution."""

    def test_first_non_empty_row_becomes_positional_header(self) -> None:
        """A SAP-style first td row is exposed as an inferred header."""
        tables = extract(
            "<table><tr><td>MANDT</td><td>TITLE</td></tr><tr><td>100</td><td>문의</td></tr></table>"
        )
        table = tables[0]
        self.assertEqual(table.headers, ("MANDT", "TITLE"))
        self.assertEqual(table.data_row_count, 1)
        self.assertIn(
            "positional_header", [diagnostic.code for diagnostic in table.diagnostics]
        )

    def test_semantic_th_header_needs_no_positional_warning(self) -> None:
        """A th row is recognized as a semantically declared header."""
        table = extract(
            "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        )[0]
        self.assertEqual(table.headers, ("A", "B"))
        self.assertNotIn(
            "positional_header", [diagnostic.code for diagnostic in table.diagnostics]
        )

    def test_whitespace_and_breaks_are_normalized(self) -> None:
        """Text normalization preserves explicit line breaks and collapses spaces."""
        table = extract(
            "<table><tr><th> A   B </th></tr><tr><td> first <br> second  value </td></tr></table>"
        )[0]
        self.assertEqual(table.rows[0][0].text, "A B")
        self.assertEqual(table.rows[1][0].text, "first\nsecond value")

    def test_nested_suppressed_elements_remain_inert(self) -> None:
        """Nested template and script elements do not escape the suppression boundary."""
        html = (
            "<template><script><table><tr><td>hidden</td></tr></table></script></template>"
            "<table><tr><th>visible</th></tr></table>"
        )
        tables = extract(html)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].headers, ("visible",))

    def test_tables_inside_suppressed_content_are_not_structural(self) -> None:
        """Template-contained tables never affect extracted document structure."""
        html = (
            "<template><table><tr><td>hidden</td></tr></table></template>"
            "<table><tr><th>visible</th></tr><tr><td>1</td></tr></table>"
        )
        tables = extract(html)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].headers, ("visible",))
        self.assertEqual(tables[0].rows[1][0].text, "1")

    def test_colspan_cannot_overlap_pending_rowspan(self) -> None:
        """Logically overlapping spans fail closed instead of overwriting cells."""
        html = (
            "<table>"
            "<tr><td>left</td><td rowspan='2'>occupied</td></tr>"
            "<tr><td colspan='2'>overlap</td></tr>"
            "</table>"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract(html)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_TABLE_SPAN)

    def test_active_content_and_resource_attributes_are_ignored(self) -> None:
        """Scripts, styles, templates, and data-URI attributes never enter cell text."""
        html = """
        <table><tr><th>BODY</th></tr><tr><td>
        visible
        <script>steal()</script><style>.x{display:none}</style>
        <noscript>fallback secret</noscript><template>template secret</template>
        <img src="data:image/png;base64,QUJDREVGRw==" alt="embedded payload">
        </td></tr></table>
        """
        text = extract(html)[0].rows[1][0].text
        self.assertEqual(text, "visible")
        self.assertNotIn("QUJD", text)
        self.assertNotIn("secret", text)

    def test_multiple_tables_preserve_document_order(self) -> None:
        """Top-level tables remain separate and preserve document order."""
        tables = extract(
            "<table><tr><td>A</td></tr></table><table><tr><td>B</td></tr></table>"
        )
        self.assertEqual([table.headers for table in tables], [("A",), ("B",)])

    def test_rowspan_and_colspan_expand_to_rectangular_grid(self) -> None:
        """Spanning cells are repeated into every covered logical coordinate."""
        html = """
        <table>
          <tr><th rowspan="2">A</th><th colspan="2">B</th></tr>
          <tr><th>C</th><th>D</th></tr>
          <tr><td>1</td><td>2</td><td>3</td></tr>
        </table>
        """
        table = extract(html)[0]
        self.assertEqual(table.column_count, 3)
        self.assertEqual(tuple(cell.text for cell in table.rows[0]), ("A", "B", "B"))
        self.assertEqual(tuple(cell.text for cell in table.rows[1]), ("A", "C", "D"))

    def test_irregular_rows_are_padded_with_empty_cells(self) -> None:
        """Short source rows normalize to the maximum logical width."""
        table = extract(
            "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td></tr></table>"
        )[0]
        self.assertEqual(tuple(cell.text for cell in table.rows[1]), ("1", ""))

    def test_empty_table_is_returned_with_zero_dimensions(self) -> None:
        """An empty table remains visible to schema inspection."""
        table = extract("<table></table>")[0]
        self.assertEqual(table.row_count, 0)
        self.assertIsNone(table.header_row_index)

    def test_nested_table_is_rejected(self) -> None:
        """Ambiguous nested tables fail closed rather than flatten silently."""
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract(
                "<table><tr><td><table><tr><td>x</td></tr></table></td></tr></table>"
            )
        self.assertEqual(caught.exception.code, ErrorCode.NESTED_TABLE)

    def test_invalid_span_is_rejected(self) -> None:
        """Non-positive or non-integer spans are invalid input."""
        for value in ("0", "-1", "abc"):
            with (
                self.subTest(value=value),
                self.assertRaises(MhtmlGatewayError) as caught,
            ):
                extract(f"<table><tr><td colspan='{value}'>x</td></tr></table>")
            self.assertEqual(caught.exception.code, ErrorCode.INVALID_TABLE_SPAN)

    def test_html_character_limit_is_enforced(self) -> None:
        """Decoded HTML cannot exceed its independent parser budget."""
        limits = ParseLimits(max_html_chars=10)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract("<table><tr><td>x</td></tr></table>", limits=limits)
        self.assertEqual(caught.exception.code, ErrorCode.HTML_TOO_LARGE)

    def test_table_count_limit_is_enforced(self) -> None:
        """A document cannot create more tables than configured."""
        limits = ParseLimits(max_tables=1)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract("<table></table><table></table>", limits=limits)
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_TABLES)

    def test_row_limit_is_enforced(self) -> None:
        """A table cannot exceed the configured source row count."""
        limits = ParseLimits(max_rows_per_table=1)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract(
                "<table><tr><td>a</td></tr><tr><td>b</td></tr></table>", limits=limits
            )
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_ROWS)

    def test_column_limit_is_enforced_after_span_expansion(self) -> None:
        """Logical columns, including colspan expansion, are bounded."""
        limits = ParseLimits(max_columns_per_table=2)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract("<table><tr><td colspan='3'>a</td></tr></table>", limits=limits)
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_COLUMNS)

    def test_cell_character_limit_is_enforced(self) -> None:
        """Cell text accumulation stops at the configured boundary."""
        limits = ParseLimits(max_cell_text_chars=3)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract("<table><tr><td>four</td></tr></table>", limits=limits)
        self.assertEqual(caught.exception.code, ErrorCode.CELL_TEXT_TOO_LARGE)

    def test_total_cell_limit_is_enforced(self) -> None:
        """The document-wide normalized cell budget prevents expansion abuse."""
        limits = ParseLimits(max_total_cells=3)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract(
                "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>",
                limits=limits,
            )
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_CELLS)

    def test_orphan_cells_outside_rows_are_ignored(self) -> None:
        """Malformed cells outside tr elements do not create phantom rows."""
        table = extract("<table><td>orphan</td><tr><td>A</td></tr></table>")[0]
        self.assertEqual(table.headers, ("A",))

    def test_block_tags_and_self_closing_breaks_are_normalized(self) -> None:
        """Block boundaries and self-closing breaks produce deterministic separators."""
        html = "<table><tr><td><div>first</div><p>second</p>third<br/>fourth</td></tr></table>"
        table = extract(html)[0]
        self.assertEqual(table.headers, ("first second third\nfourth",))

    def test_long_rowspan_decrements_across_multiple_trailing_rows(self) -> None:
        """A valid long rowspan is represented in every bounded trailing row."""
        table = extract("<table><tr><td rowspan='3'>A</td></tr></table>")[0]
        self.assertEqual(table.row_count, 3)
        self.assertEqual([row[0].text for row in table.rows], ["A", "A", "A"])

    def test_rowspan_can_generate_trailing_rows(self) -> None:
        """A rowspan extending past source rows creates explicit logical rows."""
        html = "<table><tr><td rowspan='3'>A</td><td>B</td></tr><tr><td>C</td></tr></table>"
        table = extract(html)[0]
        self.assertEqual(table.row_count, 3)
        self.assertEqual(tuple(cell.text for cell in table.rows[2]), ("A", ""))

    def test_pending_rowspan_can_leave_a_logical_gap(self) -> None:
        """Pending spans at later columns pad earlier coordinates with empty cells."""
        html = "<table><tr><td>A</td><td rowspan='2'>B</td></tr><tr></tr></table>"
        table = extract(html)[0]
        self.assertEqual(tuple(cell.text for cell in table.rows[1]), ("", "B"))

    def test_pending_rowspan_gap_can_continue_for_multiple_rows(self) -> None:
        """A later-column pending span decrements across explicit empty rows."""
        html = "<table><tr><td>A</td><td rowspan='3'>B</td></tr><tr></tr></table>"
        table = extract(html)[0]
        self.assertEqual(tuple(cell.text for cell in table.rows[1]), ("", "B"))
        self.assertEqual(tuple(cell.text for cell in table.rows[2]), ("", "B"))

    def test_trailing_rowspan_at_later_column_preserves_gap(self) -> None:
        """A trailing implicit row pads coordinates before a pending later column."""
        html = "<table><tr><td>A</td><td rowspan='2'>B</td></tr></table>"
        table = extract(html)[0]
        self.assertEqual(tuple(cell.text for cell in table.rows[1]), ("", "B"))

    def test_unrelated_self_closing_and_end_tags_are_noops(self) -> None:
        """Non-table self-closing and closing tags do not alter cell text."""
        table = extract("<table><tr><td>A<img/></span>B</td></tr></table>")[0]
        self.assertEqual(table.headers, ("AB",))

    def test_rowspan_expansion_obeys_row_limit(self) -> None:
        """Implicit rows created by rowspan cannot bypass the row budget."""
        limits = ParseLimits(max_rows_per_table=2)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract("<table><tr><td rowspan='3'>A</td></tr></table>", limits=limits)
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_ROWS)


if __name__ == "__main__":
    unittest.main()
