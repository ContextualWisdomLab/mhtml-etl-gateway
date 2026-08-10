"""Optional integration against a real ZCRHT811 MHTML (skipped if unavailable)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mhtml_etl_gateway.pipeline import extract_table

REAL = Path(
    "/Users/seonghobae/Library/Mobile Documents/com~apple~CloudDocs/"
    "Downloads/효성중공업 CRM 데이터/효성중공업CRM_2026/"
    "ZCRHT811_export_20260220_20260301.MHTML"
)


@pytest.mark.skipif(not REAL.is_file(), reason="real CRM MHTML not present on this machine")
def test_real_zcrht811_extract_headers_and_rows() -> None:
    extracted = extract_table(REAL)
    assert "MANDT" in extracted.headers
    assert "GUID" in extracted.headers
    assert len(extracted.rows) >= 1
    mandt_i = extracted.headers.index("MANDT")
    guid_i = extracted.headers.index("GUID")
    assert extracted.rows[0][mandt_i]
    assert extracted.rows[0][guid_i]
    # No mutation of raw file size via read-only extract.
    assert REAL.stat().st_size > 0
