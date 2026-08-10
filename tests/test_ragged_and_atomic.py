"""Regression: fail-closed ragged rows; atomic on_duplicate=replace."""

from __future__ import annotations

from pathlib import Path

import pytest

from mhtml_etl_gateway.html_table_extractor import extract_primary_table
from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres
from mhtml_etl_gateway.postgres_loader import InMemorySink, LoadError, load_table
from mhtml_etl_gateway.schema_inference import infer_table_schema
from mhtml_etl_gateway.validation_engine import ValidationError, validate_extracted_table


def _write_mhtml(path: Path, html: str) -> None:
    boundary = "----=_NextPart_RAGGED"
    body = (
        f'MIME-Version: 1.0\r\n'
        f'Content-Type: multipart/related; boundary="{boundary}"\r\n\r\n'
        f"--{boundary}\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n\r\n"
        f"{html}\r\n"
        f"--{boundary}--\r\n"
    )
    path.write_text(body, encoding="utf-8")


def test_extract_preserves_ragged_row_lengths() -> None:
    html = """
    <html><body><table>
      <tr><td>MANDT</td><td>GUID</td><td>TITLE</td></tr>
      <tr><td>603</td><td>ABC</td></tr>
    </table></body></html>
    """
    table = extract_primary_table(html)
    assert table.headers == ["MANDT", "GUID", "TITLE"]
    assert len(table.rows[0]) == 2  # not padded to 3


def test_pipeline_rejects_ragged_mhtml_fail_closed(tmp_path: Path) -> None:
    """AC1: inconsistent shapes must not load (no silent pad → success)."""
    path = tmp_path / "ragged.MHTML"
    html = (
        "<html><body><table>"
        "<tr><td>MANDT</td><td>GUID</td><td>TITLE</td></tr>"
        "<tr><td>603</td><td>ONLY_TWO_CELLS</td></tr>"
        "</table></body></html>"
    )
    _write_mhtml(path, html)

    with pytest.raises(ValidationError, match="cells"):
        convert_mhtml_to_postgres(
            path,
            table_name="zcrht811_export_rows",
            required_headers=["MANDT", "GUID"],
        )

    # Sink path: ensure no rows written when validation is in pipeline
    sink = InMemorySink()
    with pytest.raises(ValidationError):
        convert_mhtml_to_postgres(
            path,
            sink=sink,
            table_name="zcrht811_export_rows",
            required_headers=["MANDT", "GUID"],
        )
    assert sink.count_rows("zcrht811_export_rows") == 0


def test_validate_still_rejects_ragged_explicitly() -> None:
    with pytest.raises(ValidationError, match="cells"):
        validate_extracted_table(
            ["MANDT", "GUID", "TITLE"],
            [["603", "ABC"]],  # missing TITLE cell
        )


def test_replace_is_atomic_on_insert_failure(sample_mhtml_path: Path) -> None:
    """If insert fails after delete, prior rows + catalog must be restored."""
    sink = InMemorySink()
    r1 = convert_mhtml_to_postgres(
        sample_mhtml_path,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="replace",
    )
    assert r1["inserted_rows"] >= 1
    count_before = sink.count_rows("zcrht811_export_rows")
    sha = r1["source_sha256"]
    cat_before = sink.catalog_get(sha, "zcrht811_export_rows")
    assert cat_before is not None
    assert cat_before.status == "loaded"
    assert cat_before.row_count == count_before

    # Force failure inside atomic write after delete.
    sink.fail_after_delete = True
    schema = infer_table_schema(
        ["MANDT", "GUID"],
        [["603", "X"]],
        table_name="zcrht811_export_rows",
    )
    sink.ensure_table(schema)
    with pytest.raises(LoadError, match="simulated insert failure"):
        load_table(
            schema,
            [["603", "X"]],
            sink=sink,
            source_artifact_path=str(sample_mhtml_path),
            source_artifact_sha256=sha,
            on_duplicate="replace",
        )

    # Atomic: business rows and catalog unchanged.
    assert sink.count_rows("zcrht811_export_rows") == count_before
    cat_after = sink.catalog_get(sha, "zcrht811_export_rows")
    assert cat_after is not None
    assert cat_after.status == "loaded"
    assert cat_after.row_count == cat_before.row_count

    # Subsequent skip must not leave 0 rows permanently.
    sink.fail_after_delete = False
    r_skip = convert_mhtml_to_postgres(
        sample_mhtml_path,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="skip",
    )
    assert r_skip["skipped"] is True
    assert sink.count_rows("zcrht811_export_rows") == count_before
