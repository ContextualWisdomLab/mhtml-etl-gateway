from __future__ import annotations

import json
from pathlib import Path

import pytest

from mhtml_etl_gateway.batch import BatchError, run_batch
from mhtml_etl_gateway.postgres_loader import InMemorySink


def test_batch_report_does_not_emit_operator_directory_or_filename(
    tmp_path: Path, sample_mhtml_path: Path
) -> None:
    source = tmp_path / "operator-private-crm-export"
    source.mkdir()
    (source / "private-customer-file.MHTML").write_bytes(sample_mhtml_path.read_bytes())

    report = run_batch(
        source,
        sink=InMemorySink(),
        table_name="crm_rows",
    )
    serialized = json.dumps(report.to_dict(), ensure_ascii=False, default=str)

    assert report.source == "operator-supplied-directory"
    assert str(source) not in serialized
    assert "private-customer-file.MHTML" not in serialized
    assert report.results[0].path.startswith("artifact:")


def test_batch_failure_does_not_propagate_operator_path(
    tmp_path: Path, sample_mhtml_path: Path, monkeypatch
) -> None:
    source = tmp_path / "operator-private-crm-export"
    source.mkdir()
    (source / "private-customer-file.MHTML").write_bytes(sample_mhtml_path.read_bytes())

    def fail(path, **kwargs):
        raise RuntimeError(f"private input: {path}")

    monkeypatch.setattr("mhtml_etl_gateway.batch.convert_mhtml_to_postgres", fail)
    with pytest.raises(BatchError) as exc_info:
        run_batch(source, sink=InMemorySink(), continue_on_error=False)

    assert str(source) not in str(exc_info.value)
    assert "private-customer-file.MHTML" not in str(exc_info.value)
