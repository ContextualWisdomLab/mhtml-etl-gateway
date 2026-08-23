from __future__ import annotations

import pytest

from mhtml_etl_gateway.html_table_extractor import (
    TableExtractError,
    extract_primary_table,
    extract_tables_from_html,
)
from mhtml_etl_gateway.mhtml_parser import extract_html_bytes


def test_extract_headers_and_rows_from_fixture(sample_mhtml_bytes: bytes) -> None:
    html = extract_html_bytes(sample_mhtml_bytes)
    table = extract_primary_table(html)
    assert "MANDT" in table.headers
    assert "GUID" in table.headers
    assert table.row_count >= 1
    # First data row should carry known fixture values.
    mandt_i = table.headers.index("MANDT")
    guid_i = table.headers.index("GUID")
    assert table.rows[0][mandt_i] == "603"
    assert table.rows[0][guid_i] == "0050569512931FE183BEBA5F974B88B9"


def test_nested_table_does_not_split_rows() -> None:
    html = """
    <html><body><table>
      <tr><td>MANDT</td><td>GUID</td><td>VOCCTS</td></tr>
      <tr><td>603</td><td>ABC</td><td>outer
        <table><tr><td>nested</td></tr></table>
      more</td></tr>
    </table></body></html>
    """
    table = extract_primary_table(html)
    assert table.headers == ["MANDT", "GUID", "VOCCTS"]
    assert table.row_count == 1
    assert table.rows[0][0] == "603"
    assert "nested" in table.rows[0][2]
    assert "more" in table.rows[0][2]


def test_empty_html_fails_closed() -> None:
    with pytest.raises(TableExtractError):
        extract_tables_from_html("")
    with pytest.raises(TableExtractError):
        extract_primary_table("<html><body>no tables</body></html>")


def test_colspan_expands_header_cells() -> None:
    html = """
    <html><body><table>
      <tr><td colspan="2">MERGED</td><td>C</td></tr>
      <tr><td>a</td><td>b</td><td>c</td></tr>
    </table></body></html>
    """
    table = extract_primary_table(html)
    assert table.headers == ["MERGED", "MERGED", "C"]
    assert table.rows[0] == ["a", "b", "c"]


def test_colspan_dos_protection() -> None:
    html = """
    <html><body><table>
      <tr><td colspan="1000000">TOO_BIG</td></tr>
    </table></body></html>
    """
    with pytest.raises(TableExtractError, match="colspan too large"):
        extract_primary_table(html)


def test_active_content_and_resource_attributes_are_ignored() -> None:
    html = """
    <table><tr><th>BODY</th></tr><tr><td>
    visible
    <script>steal()</script><style>.x{display:none}</style>
    <noscript>fallback secret</noscript><template>template secret</template>
    <img src="data:image/png;base64,QUJDREVGRw==" alt="embedded payload">
    </td></tr></table>
    """
    table = extract_primary_table(html)
    assert table.rows[0][0] == "visible"
    assert "steal()" not in table.rows[0][0]
    assert "secret" not in table.rows[0][0]


def test_nested_suppression_recovers_visible_text_after_resources() -> None:
    html = """
    <table><tr><th>BODY</th></tr><tr><td>visible-before
    <template>hidden<div>ignored markup</div><iframe>nested hidden</iframe></template>
    <object>object hidden</object><embed src="data:text/plain,hidden">
    visible-after</td></tr></table>
    """

    table = extract_primary_table(html)
    value = table.rows[0][0]
    assert "visible-before" in value
    assert "visible-after" in value
    assert "hidden" not in value


def test_mismatched_suppression_closer_keeps_outer_boundary() -> None:
    """A stray closer must not expose text that remains inside a template."""

    html = (
        "<table><tr><th>BODY</th></tr><tr><td>visible"
        "<template><style></style></style>secret</template>after"
        "</td></tr></table>"
    )

    table = extract_primary_table(html)
    assert table.rows == [["visibleafter"]]
    assert "secret" not in table.rows[0][0]


def test_unclosed_suppression_inside_table_fails_closed() -> None:
    """An unclosed active-content boundary inside a table remains an error."""

    html = "<table><tr><th>BODY</th></tr><tr><td>visible<object>hidden</td></tr></table>"
    with pytest.raises(TableExtractError, match="suppression container"):
        extract_primary_table(html)


def test_unclosed_suppression_outside_table_does_not_hide_following_table() -> None:
    """Malformed non-table markup must not deny extraction of a later table."""

    html = (
        "<html><head><style>body{display:none}</head><body>"
        "<table><tr><th>BODY</th></tr><tr><td>visible</td></tr></table>"
        "</body></html>"
    )

    table = extract_primary_table(html)
    assert table.headers == ["BODY"]
    assert table.rows == [["visible"]]


def test_ignored_void_resource_tag() -> None:
    html = (
        "<table><tr><th>BODY</th></tr><tr><td>visible"
        "<embed src='data:image/png;base64,QUJDREVGRw==' alt='embedded payload'>after"
        "</td></tr></table>"
    )
    table = extract_primary_table(html)
    assert table.rows[0][0] == "visibleafter"


def test_unclosed_suppression_outside_table_recovers_across_feed_chunks() -> None:
    """Recovery must also hold when the later table begins in a later feed chunk."""

    html = (
        "<html><head><style>body{display:none}</head><body>"
        + ("x" * 256 * 1024)
        + "<table><tr><th>BODY</th></tr><tr><td>visible</td></tr></table>"
        "</body></html>"
    )

    table = extract_primary_table(html)
    assert table.headers == ["BODY"]
    assert table.rows == [["visible"]]


def test_decoded_markup_remains_internal_table_data() -> None:
    html = """
    <table>
      <tr><th>&lt;script&gt;header()&lt;/script&gt;</th>
          <th x:str="&lt;script&gt;xheader()&lt;/script&gt;"></th></tr>
      <tr><td>&lt;script&gt;row()&lt;/script&gt;</td>
          <td x:str="&lt;script&gt;xrow()&lt;/script&gt;"></td></tr>
    </table>
    """

    table = extract_primary_table(html)
    assert table.headers == ["<script>header()</script>", "<script>xheader()</script>"]
    assert table.rows == [["<script>row()</script>", "<script>xrow()</script>"]]
