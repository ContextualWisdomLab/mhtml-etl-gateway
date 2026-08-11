"""Tests for immutable parser and report models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.models import (
    Diagnostic,
    ExtractedTable,
    InspectionReport,
    MhtmlDocument,
    ParseLimits,
    TableCell,
    TableInspection,
)


class ModelContractTests(unittest.TestCase):
    """Verify model validation and serialization contracts."""

    def test_parse_limits_reject_non_positive_values(self) -> None:
        """Every configured limit must be positive."""
        with self.assertRaisesRegex(ValueError, "max_source_bytes"):
            ParseLimits(max_source_bytes=0)

    def test_models_are_immutable(self) -> None:
        """Parsed source identity cannot be mutated after construction."""
        document = MhtmlDocument(
            html_text="<html></html>",
            root_content_type="text/html",
            root_content_location=None,
            root_content_id=None,
            diagnostics=(),
        )
        with self.assertRaises(FrozenInstanceError):
            document.html_text = "changed"  # type: ignore[misc]

    def test_extracted_table_requires_rectangular_rows(self) -> None:
        """A normalized table cannot contain rows of different widths."""
        with self.assertRaisesRegex(ValueError, "rectangular"):
            ExtractedTable(
                rows=(
                    (TableCell("a", False),),
                    (TableCell("b", False), TableCell("c", False)),
                ),
                header_row_index=0,
                diagnostics=(),
            )

    def test_extracted_table_rejects_invalid_header_index(self) -> None:
        """The declared header row must exist."""
        with self.assertRaisesRegex(ValueError, "header_row_index"):
            ExtractedTable(
                rows=((TableCell("a", True),),),
                header_row_index=2,
                diagnostics=(),
            )

    def test_empty_table_can_have_no_header(self) -> None:
        """An empty table has no header row and zero dimensions."""
        table = ExtractedTable(rows=(), header_row_index=None, diagnostics=())
        self.assertEqual(table.row_count, 0)
        self.assertEqual(table.column_count, 0)
        self.assertEqual(table.headers, ())
        self.assertEqual(table.header_source, "none")

    def test_table_properties_expose_dimensions_and_headers_internally(self) -> None:
        """Internal extraction properties derive from normalized cells."""
        table = ExtractedTable(
            rows=(
                (TableCell("MANDT", True), TableCell("TITLE", True)),
                (TableCell("100", False), TableCell("문의", False)),
            ),
            header_row_index=0,
            diagnostics=(Diagnostic("positional_header", "Header inferred"),),
        )
        self.assertEqual(table.row_count, 2)
        self.assertEqual(table.data_row_count, 1)
        self.assertEqual(table.column_count, 2)
        self.assertEqual(table.headers, ("MANDT", "TITLE"))
        self.assertEqual(table.header_source, "semantic")

    def test_positional_header_source_is_explicit(self) -> None:
        """A cell-derived first row is distinguished from semantic th markup."""
        table = ExtractedTable(
            rows=((TableCell("MANDT", False),),),
            header_row_index=0,
            diagnostics=(Diagnostic("positional_header", "Header inferred"),),
        )
        self.assertEqual(table.header_source, "positional")

    def test_inspection_report_serialization_excludes_values_and_ordinals(self) -> None:
        """The public report exposes structure but no source row or table identity."""
        report = InspectionReport(
            source_hash_sha256="a" * 64,
            source_size_bytes=123,
            root_content_location_hash_sha256="b" * 64,
            diagnostics=(
                Diagnostic("identity_transfer_encoding", "Used identity decoding"),
            ),
            tables=(
                TableInspection(
                    row_count=2,
                    data_row_count=1,
                    column_count=2,
                    header_row_index=0,
                    header_source="semantic",
                    header_value_count=2,
                    diagnostics=(),
                ),
            ),
        )
        serialized = report.to_dict()
        self.assertEqual(serialized["table_count"], 1)
        self.assertNotIn("table_index", serialized["tables"][0])
        self.assertNotIn("headers", serialized["tables"][0])
        self.assertEqual(serialized["root_content_location_hash_sha256"], "b" * 64)
        self.assertNotIn("root_content_type", serialized)
        self.assertNotIn("root_content_location_scheme", serialized)
        self.assertNotIn("rows", serialized["tables"][0])
        self.assertNotIn("문의", repr(serialized))

    def test_error_serialization_discards_caller_detail(self) -> None:
        """Expected failures expose a fixed JSON-ready message per error code."""
        error = MhtmlGatewayError(ErrorCode.INVALID_MIME, "attacker controlled")
        self.assertEqual(
            error.to_dict(),
            {"error_code": "invalid_mime", "message": "MHTML input is invalid"},
        )
        self.assertNotIn("attacker", str(error))


if __name__ == "__main__":
    unittest.main()
