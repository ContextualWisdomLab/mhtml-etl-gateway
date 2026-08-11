"""Optional integration against a real ZCRHT811 MHTML (path via env only)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mhtml_etl_gateway.pipeline import extract_table

# Local-only path. Do not commit absolute CRM / iCloud paths into the repo.
_REAL_ENV = os.environ.get("MHTML_ETL_REAL_SAMPLE", "").strip()
REAL = Path(_REAL_ENV) if _REAL_ENV else None


@pytest.mark.skipif(
    REAL is None or not REAL.is_file(),
    reason="Set MHTML_ETL_REAL_SAMPLE to a local .MHTML path to enable this test",
)
def test_real_zcrht811_extract_headers_and_rows() -> None:
    assert REAL is not None
    extracted = extract_table(REAL)
    assert "MANDT" in extracted.headers
    assert "GUID" in extracted.headers
    assert len(extracted.rows) >= 1
    mandt_i = extracted.headers.index("MANDT")
    guid_i = extracted.headers.index("GUID")
    assert extracted.rows[0][mandt_i]
    assert extracted.rows[0][guid_i]
    # Read-only extract; raw file must still exist with non-zero size.
    assert REAL.stat().st_size > 0
