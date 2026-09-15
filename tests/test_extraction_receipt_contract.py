"""Contract tests for owner-issued MHTML extraction provenance receipts."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

import pytest

from mhtml_etl_gateway.extraction_receipt import (
    EXTRACTION_RECEIPT_SCHEMA_VERSION,
    EXTRACTION_RECEIPT_WIRE_BYTE_LIMIT,
    ValidatedExtractionReceiptWireV1,
    extract_table_with_receipt,
)

from tests.fixture_factory import make_mhtml


IMMUTABLE_RELEASE = "v0.4.0@779254927abb1e7cee80fd949907ccd03f9fc7be"


def _source() -> bytes:
    return make_mhtml(
        "<html><body><table>"
        "<tr><th>이름</th><th>점수</th></tr>"
        "<tr><td>민수</td><td>7</td></tr>"
        "<tr><td>지현</td><td>9</td></tr>"
        "</table></body></html>"
    )


def _output_digest(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> str:
    canonical = json.dumps(
        {"headers": headers, "rows": rows},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_real_extraction_mints_value_free_immutable_receipt() -> None:
    source = _source()

    bound = extract_table_with_receipt("ignored.mhtml", data=source)
    receipt = bound.receipt

    assert bound.headers == ("이름", "점수")
    assert bound.rows == (("민수", "7"), ("지현", "9"))
    assert receipt.source_sha256 == hashlib.sha256(source).hexdigest()
    assert receipt.source_size_bytes == len(source)
    assert receipt.source_artifact_ref == f"artifact:{receipt.source_sha256[:16]}"
    assert receipt.output_sha256 == _output_digest(bound.headers, bound.rows)
    assert receipt.implementation_release == IMMUTABLE_RELEASE
    assert UUID(receipt.receipt_id).version == 7

    wire = receipt.to_json()
    for protected_value in ("이름", "점수", "민수", "지현"):
        assert protected_value not in wire
    validated = ValidatedExtractionReceiptWireV1.from_json(wire)
    assert validated.binding_sha256() == receipt.binding_sha256()


def test_one_receipt_cannot_validate_different_extracted_output() -> None:
    bound = extract_table_with_receipt("ignored.mhtml", data=_source())
    changed_rows = (("민수", "7"), ("지현", "10"))

    assert bound.receipt.matches_output(bound.headers, bound.rows)
    assert not bound.receipt.matches_output(bound.headers, changed_rows)


def test_canonical_wire_rejects_mutable_release_noncanonical_and_oversized_input() -> None:
    receipt = extract_table_with_receipt("ignored.mhtml", data=_source()).receipt
    wire = receipt.to_json()

    with pytest.raises(ValueError):
        ValidatedExtractionReceiptWireV1.from_json(" " + wire)

    payload = json.loads(wire)
    payload["implementation_release"] = "main"
    with pytest.raises(ValueError):
        ValidatedExtractionReceiptWireV1.from_json(
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
        )

    with pytest.raises(ValueError):
        ValidatedExtractionReceiptWireV1.from_json(
            "x" * (EXTRACTION_RECEIPT_WIRE_BYTE_LIMIT + 1)
        )


def test_binding_changes_when_any_derivation_authority_changes() -> None:
    receipt = extract_table_with_receipt("ignored.mhtml", data=_source()).receipt
    baseline = json.loads(receipt.to_json())

    alternatives = {
        "output_sha256": "0" * 64,
        "configuration_sha256": "1" * 64,
        "implementation_release": "v0.4.1@" + "2" * 40,
        "selected_component": "primary-table:index-0",
    }
    for field, value in alternatives.items():
        changed = dict(baseline)
        changed[field] = value
        wire = json.dumps(changed, sort_keys=True, separators=(",", ":"))
        validated = ValidatedExtractionReceiptWireV1.from_json(wire)
        assert validated.binding_sha256() != receipt.binding_sha256()


def test_schema_constant_is_versioned_and_canonical() -> None:
    assert EXTRACTION_RECEIPT_SCHEMA_VERSION == "mhtml_etl_gateway.extraction_receipt.v1"
