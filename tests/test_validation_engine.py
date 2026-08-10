from __future__ import annotations

import pytest

from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres
from mhtml_etl_gateway.validation_engine import (
    ValidationError,
    validate_extracted_table,
)


def test_validate_requires_mandt_guid_for_zcrht_shape() -> None:
    with pytest.raises(ValidationError, match="missing required headers"):
        validate_extracted_table(
            ["TITLE", "AMOUNT"],
            [["a", "1"]],
            table_name="zcrht811_export_rows",
        )


def test_validate_pass_with_mandt_guid() -> None:
    result = validate_extracted_table(
        ["MANDT", "GUID", "TITLE"],
        [["603", "ABC", "t"]],
    )
    assert result.ok
    assert result.row_count == 1
    assert "MANDT" in result.required_headers


def test_validate_case_insensitive_required_headers() -> None:
    result = validate_extracted_table(
        ["mandt", "guid", "TITLE"],
        [["603", "ABC", "t"]],
    )
    assert result.ok


def test_zcrht_hint_headers_require_mandt_guid_without_table_name() -> None:
    # DOCNOSUB + VOCTP imply ZCRHT family even if MANDT/GUID missing.
    with pytest.raises(ValidationError, match="missing required headers"):
        validate_extracted_table(
            ["DOCNOSUB", "VOCTP", "TITLE"],
            [["x", "VOC", "t"]],
        )


def test_validate_empty_rows_fails() -> None:
    with pytest.raises(ValidationError, match="no data rows"):
        validate_extracted_table(["MANDT", "GUID"], [])


def test_validate_ragged_row_fails() -> None:
    with pytest.raises(ValidationError, match="cells"):
        validate_extracted_table(
            ["MANDT", "GUID"],
            [["603"]],
        )


def test_pipeline_rejects_missing_required_headers(sample_mhtml_path, tmp_path) -> None:
    # Craft minimal invalid MHTML without MANDT/GUID
    bad = tmp_path / "bad.MHTML"
    boundary = "----=_NextPart_TEST"
    html = (
        "<html><body><table>"
        "<tr><td>TITLE</td><td>X</td></tr>"
        "<tr><td>hello</td><td>1</td></tr>"
        "</table></body></html>"
    )
    body = (
        f'MIME-Version: 1.0\r\n'
        f'Content-Type: multipart/related; boundary="{boundary}"\r\n\r\n'
        f"--{boundary}\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n\r\n"
        f"{html}\r\n"
        f"--{boundary}--\r\n"
    )
    bad.write_text(body, encoding="utf-8")
    with pytest.raises(ValidationError):
        convert_mhtml_to_postgres(
            bad,
            table_name="zcrht811_export_rows",
            required_headers=["MANDT", "GUID"],
        )
