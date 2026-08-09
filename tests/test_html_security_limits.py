"""Focused security and allocation tests for HTML table extraction."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.html_tables import extract_tables
from mhtml_etl_gateway.mime_parser import parse_mhtml_bytes
from mhtml_etl_gateway.models import ParseLimits
from tests.fixture_factory import make_mhtml


def _extract(html_text: str, limits: ParseLimits):
    """Parse synthetic MHTML and extract its tables under explicit limits."""
    document = parse_mhtml_bytes(make_mhtml(html_text), limits=limits)
    return extract_tables(document, limits=limits)


class HtmlSecurityLimitTests(unittest.TestCase):
    """Verify inert resources and pre-allocation budget enforcement."""

    def test_span_budget_fails_before_logical_cell_allocation(self) -> None:
        """A huge rowspan and colspan projection is rejected before allocation."""
        limits = ParseLimits(
            max_rows_per_table=1_000_000,
            max_columns_per_table=4096,
            max_total_cells=64,
        )
        html_text = (
            "<table><tr><td rowspan='1000000' colspan='4096'>"
            "x</td></tr></table>"
        )
        with patch(
            "mhtml_etl_gateway.html_tables.TableCell",
            side_effect=AssertionError("logical cell allocation occurred"),
        ):
            with self.assertRaises(MhtmlGatewayError) as caught:
                _extract(html_text, limits)
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_CELLS)

    def test_embedded_resource_descendants_are_suppressed(self) -> None:
        """Iframe, object, and embed descendants never enter extracted text."""
        limits = ParseLimits()
        for tag_name in ("iframe", "object", "embed"):
            with self.subTest(tag_name=tag_name):
                opening = "<" + tag_name + ">"
                closing = "</" + tag_name + ">"
                html_text = (
                    "<table><tr><td>visible"
                    + opening
                    + "secret"
                    + closing
                    + "after</td></tr></table>"
                )
                table = _extract(html_text, limits)[0]
                self.assertEqual(table.headers, ("visibleafter",))


if __name__ == "__main__":
    unittest.main()
