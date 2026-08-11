from __future__ import annotations

import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_MHTML = FIXTURES / "zcrht811_sample.MHTML"

# Optional real CRM sample: set MHTML_ETL_REAL_SAMPLE to an absolute .MHTML path locally.
# Never hardcode machine/user data paths in the repository.
REAL_CRM_SMALL = Path(os.environ["MHTML_ETL_REAL_SAMPLE"]) if os.environ.get("MHTML_ETL_REAL_SAMPLE") else None


@pytest.fixture
def sample_mhtml_path() -> Path:
    assert SAMPLE_MHTML.is_file(), f"missing fixture: {SAMPLE_MHTML}"
    return SAMPLE_MHTML


@pytest.fixture
def sample_mhtml_bytes(sample_mhtml_path: Path) -> bytes:
    return sample_mhtml_path.read_bytes()
