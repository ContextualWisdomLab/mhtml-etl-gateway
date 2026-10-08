"""Regression coverage for ambiguous spans and raw-cell allocation budgets."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.html_tables import _RawCell, extract_tables
from mhtml_etl_gateway.mime_parser import parse_mhtml_bytes
from mhtml_etl_gateway.models import ParseLimits
from tests.fixture_factory import make_mhtml


class HtmlParserInputBudgetTests(unittest.TestCase):
    """Reject ambiguous attributes and excessive raw cells before allocation."""

    def test_duplicate_span_attributes_fail_closed_case_insensitively(self) -> None:
        """Mixed-case duplicate rowspan and colspan attributes are ambiguous."""
        for attributes in (
            "rowspan='2' ROWSPAN='3'",
            "colspan='2' COLSPAN='3'",
        ):
            with self.subTest(attributes=attributes):
                source = make_mhtml(f"<table><tr><td {attributes}>x</td></tr></table>")
                with self.assertRaises(MhtmlGatewayError) as caught:
                    extract_tables(parse_mhtml_bytes(source))
                self.assertEqual(caught.exception.code, ErrorCode.INVALID_TABLE_SPAN)

    def test_raw_cell_budget_fails_before_the_excess_cell_is_allocated(self) -> None:
        """The sixty-fifth source cell is rejected before `_RawCell` construction."""
        source = make_mhtml("<table><tr>" + "<td>x</td>" * 65 + "</tr></table>")
        created_cells = 0

        def create_raw_cell(*args, **kwargs):
            nonlocal created_cells
            created_cells += 1
            return _RawCell(*args, **kwargs)

        limits = ParseLimits(
            max_columns_per_table=128,
            max_total_cells=64,
        )
        with patch(
            "mhtml_etl_gateway.html_tables._RawCell",
            side_effect=create_raw_cell,
        ):
            with self.assertRaises(MhtmlGatewayError) as caught:
                document = parse_mhtml_bytes(source, limits=limits)
                extract_tables(document, limits=limits)
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_CELLS)
        self.assertEqual(created_cells, 64)


if __name__ == "__main__":
    unittest.main()
