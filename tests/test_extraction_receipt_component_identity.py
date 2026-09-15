"""Regression contract for concrete MHTML extraction component identity."""

from __future__ import annotations

import copy

import pytest

from mhtml_etl_gateway.extraction_receipt import extract_table_with_receipt
from tests.fixture_factory import make_mhtml


def test_receipt_binds_selected_mime_part_and_table_ordinals() -> None:
    """The receipt identifies the concrete selected MIME part and table, not only policy."""

    source = make_mhtml(
        "<html><body>"
        "<table><tr><th>small_header</th></tr><tr><td>one</td></tr></table>"
        "<table><tr><th>left_header</th><th>right_header</th></tr>"
        "<tr><td>one</td><td>two</td></tr>"
        "<tr><td>three</td><td>four</td></tr></table>"
        "</body></html>",
        include_decoy=True,
    )

    bound = extract_table_with_receipt("ignored.mhtml", data=source)

    assert bound.headers == ("left_header", "right_header")
    assert bound.rows == (("one", "two"), ("three", "four"))
    assert bound.receipt.selected_component == "mime-part:1.table:1"
    assert "left_header" not in bound.receipt.to_json()
    assert "right_header" not in bound.receipt.to_json()


def test_owner_serialization_rejects_valid_shape_component_substitution() -> None:
    """A copied owner receipt cannot swap one concrete locator for another."""

    receipt = extract_table_with_receipt("ignored.mhtml", data=make_mhtml(
        "<html><body><table><tr><th>header</th></tr>"
        "<tr><td>value</td></tr></table></body></html>"
    )).receipt
    forged = copy.copy(receipt)
    object.__setattr__(forged, "selected_component", "mime-part:9.table:9")

    with pytest.raises(ValueError):
        forged.to_json()
