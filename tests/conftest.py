from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_MHTML = FIXTURES / "zcrht811_sample.MHTML"

# Optional real CRM path (launch/evidence only; unit tests use fixture).
REAL_CRM_SMALL = Path(
    "/Users/seonghobae/Library/Mobile Documents/com~apple~CloudDocs/"
    "Downloads/효성중공업 CRM 데이터/효성중공업CRM_2026/"
    "ZCRHT811_export_20260220_20260301.MHTML"
)


@pytest.fixture
def sample_mhtml_path() -> Path:
    assert SAMPLE_MHTML.is_file(), f"missing fixture: {SAMPLE_MHTML}"
    return SAMPLE_MHTML


@pytest.fixture
def sample_mhtml_bytes(sample_mhtml_path: Path) -> bytes:
    return sample_mhtml_path.read_bytes()
