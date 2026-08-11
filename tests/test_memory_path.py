from __future__ import annotations

from mhtml_etl_gateway.html_table_extractor import extract_primary_table
from mhtml_etl_gateway.mhtml_parser import extract_html_bytes, read_mhtml_file


def test_single_read_extract_no_double_disk(sample_mhtml_path) -> None:
    """read once → html part → table; headers present (shipped path)."""
    raw = read_mhtml_file(sample_mhtml_path)
    html = extract_html_bytes(raw)
    # HTML part should be smaller than or equal to full MHTML (not a second full copy of garbage)
    assert len(html) <= len(raw)
    assert len(html) > 0
    table = extract_primary_table(html)
    assert "MANDT" in table.headers
    assert "GUID" in table.headers
    assert table.row_count >= 1


def test_chunked_feed_large_string() -> None:
    """Chunked parser feed still extracts tables correctly on larger HTML."""
    # Build HTML larger than _FEED_CHUNK (256 KiB) to force multi-chunk feed.
    rows = ["<tr><td>MANDT</td><td>GUID</td><td>TITLE</td></tr>"]
    pad = "x" * 400
    n_rows = 1200
    for i in range(n_rows):
        rows.append(f"<tr><td>603</td><td>GUID{i:04d}{pad}</td><td>t{i}</td></tr>")
    html = "<html><body><table>" + "".join(rows) + "</table></body></html>"
    assert len(html) > 256 * 1024  # larger than _FEED_CHUNK
    table = extract_primary_table(html)
    assert table.headers == ["MANDT", "GUID", "TITLE"]
    assert table.row_count == n_rows
