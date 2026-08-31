"""Regression tests for table-expansion allocation safety."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.html_tables import extract_tables
from mhtml_etl_gateway.models import MhtmlDocument, ParseLimits


class TableBudgetRegressionTests(unittest.TestCase):
    """Prove hostile spans fail before logical-cell objects are allocated."""

    def test_huge_span_fails_before_any_logical_cell_allocation(self) -> None:
        """A tiny source cannot request billions of cells before the budget check."""
        document = MhtmlDocument(
            html_text=(
                "<table><tr><td rowspan='1000000' colspan='4096'>x</td>" "</tr></table>"
            ),
            root_content_type="text/html",
            root_content_location=None,
            root_content_id=None,
            diagnostics=(),
        )
        limits = ParseLimits(
            max_rows_per_table=1_000_000,
            max_columns_per_table=4096,
            max_total_cells=10,
        )

        with (
            patch(
                "mhtml_etl_gateway.html_tables.TableCell",
                side_effect=AssertionError(
                    "logical cells were allocated before preflight"
                ),
            ),
            self.assertRaises(MhtmlGatewayError) as caught,
        ):
            extract_tables(document, limits=limits)

        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_CELLS)


if __name__ == "__main__":
    unittest.main()
