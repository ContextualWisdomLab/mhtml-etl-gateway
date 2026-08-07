"""Tests for metadata-only MHTML inspection."""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from mhtml_etl_gateway.inspection import inspect_mhtml_bytes, inspect_mhtml_file
from tests.fixture_factory import make_mhtml


class InspectionTests(unittest.TestCase):
    """Verify lineage and table summary behavior."""

    def test_default_report_excludes_all_header_values(self) -> None:
        """Metadata-only inspection never reveals semantic or inferred cell values."""
        source = make_mhtml(
            "<table><tr><th>customer_name</th><th>account_token</th></tr>"
            "<tr><td>Alice</td><td>secret</td></tr></table>"
        )
        table = inspect_mhtml_bytes(source).tables[0]
        self.assertEqual(table.headers, ())
        self.assertFalse(table.header_values_included)
        self.assertEqual(table.header_value_count, 2)
        self.assertEqual(table.header_source, "semantic")
        self.assertNotIn("customer_name", repr(table.to_dict()))
        self.assertNotIn("account_token", repr(table.to_dict()))

    def test_header_values_require_explicit_opt_in(self) -> None:
        """A protected local caller may explicitly request header values for mapping."""
        source = make_mhtml("<table><tr><td>MANDT</td><td>TITLE</td></tr></table>")
        table = inspect_mhtml_bytes(source, include_header_values=True).tables[0]
        self.assertEqual(table.headers, ("MANDT", "TITLE"))
        self.assertTrue(table.header_values_included)
        self.assertEqual(table.header_source, "positional")

    def test_content_location_is_hashed_instead_of_exposed(self) -> None:
        """Source paths and URL tokens never appear in default inspection output."""
        location = "file:///Users/Alice/customer-42/root.html?token=top-secret"
        source = make_mhtml("<table><tr><th>A</th></tr></table>", content_location=location)
        serialized = inspect_mhtml_bytes(source).to_dict()
        rendered = repr(serialized)
        self.assertNotIn("Alice", rendered)
        self.assertNotIn("top-secret", rendered)
        self.assertNotIn("root_content_location", serialized)
        self.assertEqual(serialized["root_content_location_scheme"], "file")
        self.assertEqual(
            serialized["root_content_location_hash_sha256"],
            hashlib.sha256(location.encode("utf-8")).hexdigest(),
        )

    def test_header_disclosure_flag_requires_boolean(self) -> None:
        """Accidental truthy objects cannot enable cell-derived value disclosure."""
        source = make_mhtml("<table><tr><th>A</th></tr></table>")
        with self.assertRaisesRegex(ValueError, "must be a boolean"):
            inspect_mhtml_bytes(source, include_header_values="yes")  # type: ignore[arg-type]

    def test_invalid_content_location_is_hashed_without_reflection(self) -> None:
        """Malformed location syntax remains non-sensitive and explicitly classified."""
        location = "http://[private-host"
        source = make_mhtml("<table><tr><th>A</th></tr></table>", content_location=location)
        serialized = inspect_mhtml_bytes(source).to_dict()
        self.assertEqual(serialized["root_content_location_scheme"], "invalid")
        self.assertNotIn("private-host", repr(serialized))

    def test_missing_content_location_has_no_location_metadata(self) -> None:
        """A source without Content-Location emits two explicit null metadata fields."""
        source = make_mhtml("<table><tr><th>A</th></tr></table>", content_location=None)
        serialized = inspect_mhtml_bytes(source).to_dict()
        self.assertIsNone(serialized["root_content_location_scheme"])
        self.assertIsNone(serialized["root_content_location_hash_sha256"])

    def test_report_contains_hash_dimensions_and_no_values(self) -> None:
        """Inspection binds metadata to bytes without exposing data rows."""
        source = make_mhtml("<table><tr><th>A</th><th>B</th></tr><tr><td>secret-one</td><td>secret-two</td></tr></table>")
        report = inspect_mhtml_bytes(source)
        self.assertEqual(report.source_hash_sha256, hashlib.sha256(source).hexdigest())
        self.assertEqual(report.source_size_bytes, len(source))
        self.assertEqual(report.tables[0].column_count, 2)
        self.assertEqual(report.tables[0].data_row_count, 1)
        self.assertNotIn("secret-one", repr(report.to_dict()))
        self.assertNotIn("secret-two", repr(report.to_dict()))

    def test_report_combines_document_and_table_diagnostics(self) -> None:
        """Identity decoding and positional headers remain auditable."""
        source = make_mhtml(
            "<table><tr><td>A</td></tr><tr><td>1</td></tr></table>",
            content_transfer_encoding="text/html",
        )
        report = inspect_mhtml_bytes(source)
        self.assertIn("identity_transfer_encoding", [item.code for item in report.diagnostics])
        self.assertIn("positional_header", [item.code for item in report.tables[0].diagnostics])

    def test_file_inspection_reads_bytes_once_for_identity(self) -> None:
        """The file API returns the same identity as byte inspection."""
        source = make_mhtml("<table><tr><td>A</td></tr></table>")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(source)
            self.assertEqual(inspect_mhtml_file(path), inspect_mhtml_bytes(source))


if __name__ == "__main__":
    unittest.main()
