from __future__ import annotations

import json
from pathlib import Path

from mhtml_etl_gateway.batch import run_batch
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
