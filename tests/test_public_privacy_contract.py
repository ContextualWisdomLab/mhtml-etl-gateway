"""Public privacy and error-contract regressions."""

from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from mhtml_etl_gateway.cli import main
from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.inspection import inspect_mhtml_bytes
from tests.fixture_factory import make_mhtml


class PublicPrivacyContractTests(unittest.TestCase):
    """Ensure public output cannot expose protected source-derived metadata."""

    def test_inspection_api_has_no_header_value_disclosure_switch(self) -> None:
        """Cell-derived header values are unavailable before authorization exists."""
        parameters = inspect.signature(inspect_mhtml_bytes).parameters
        self.assertNotIn("include_header_values", parameters)

    def test_default_report_omits_source_media_location_and_table_ordinals(self) -> None:
        """Public JSON contains structural counts but no protected classifications."""
        source = make_mhtml(
            "<table><tr><th>customer_name</th></tr><tr><td>Alice</td></tr></table>",
            content_location="file:///private/customer/root.html",
        )
        payload = inspect_mhtml_bytes(source).to_dict()
        rendered = repr(payload)

        self.assertNotIn("root_content_type", payload)
        self.assertNotIn("root_content_location_scheme", payload)
        self.assertIn("root_content_location_hash_sha256", payload)
        self.assertNotIn("table_index", rendered)
        self.assertNotIn("headers", rendered)
        self.assertNotIn("header_values_included", rendered)
        self.assertNotIn("customer_name", rendered)
        self.assertNotIn("Alice", rendered)
        self.assertNotIn("private", rendered)

    def test_error_serialization_uses_fixed_message_for_each_code(self) -> None:
        """Callers cannot reflect attacker-controlled text through error JSON."""
        error = MhtmlGatewayError(ErrorCode.INVALID_MIME)
        payload = error.to_dict()
        self.assertEqual(payload["error_code"], "invalid_mime")
        self.assertEqual(payload["message"], "MHTML input is invalid")
        self.assertNotIn("attacker", repr(payload))

    def test_cli_argument_failures_are_json(self) -> None:
        """Missing commands and invalid integers follow the normal JSON error contract."""
        for arguments in ([], ["inspect", "source.mhtml", "--max-source-bytes", "bad"]):
            with self.subTest(arguments=arguments):
                stderr = StringIO()
                with redirect_stderr(stderr):
                    return_code = main(arguments)
                payload = json.loads(stderr.getvalue())
                self.assertEqual(return_code, 2)
                self.assertEqual(payload["error_code"], "invalid_argument")

    def test_removed_header_flag_is_rejected_as_json(self) -> None:
        """The former local disclosure flag is no longer accepted by the CLI."""
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.mhtml"
            source_path.write_bytes(make_mhtml("<table><tr><th>A</th></tr></table>"))
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = main(
                    ["inspect", str(source_path), "--include-header-values"]
                )
        payload = json.loads(stderr.getvalue())
        self.assertEqual(return_code, 2)
        self.assertEqual(payload["error_code"], "invalid_argument")


if __name__ == "__main__":
    unittest.main()
