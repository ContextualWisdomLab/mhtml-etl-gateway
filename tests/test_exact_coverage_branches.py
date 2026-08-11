"""Focused coverage for fail-closed integrity branches."""

from __future__ import annotations

from email.message import Message
import unittest
from unittest.mock import patch

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.html_tables import extract_tables
from mhtml_etl_gateway.mime_parser import _select_html_root
from mhtml_etl_gateway.models import MhtmlDocument, ParseLimits


class ExactCoverageBranchTests(unittest.TestCase):
    """Exercise defensive branches that ordinary valid inputs cannot reach."""

    @staticmethod
    def _document(html_text: str) -> MhtmlDocument:
        """Build an inert decoded document for table-extractor boundary tests."""
        return MhtmlDocument(
            html_text=html_text,
            root_content_type="text/html",
            root_content_location=None,
            root_content_id=None,
            diagnostics=(),
        )

    def test_table_projection_integrity_mismatch_fails_closed(self) -> None:
        """A disagreement between projected and realized shape is never accepted."""
        document = self._document("<table><tr><td>A</td></tr></table>")
        with patch(
            "mhtml_etl_gateway.html_tables._project_table_shape",
            return_value=(2, 1),
        ):
            with self.assertRaises(MhtmlGatewayError) as caught:
                extract_tables(document)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_TABLE_SPAN)

    def test_direct_table_extraction_enforces_decoded_html_limit(self) -> None:
        """Callers cannot bypass the extractor's own decoded-character budget."""
        document = self._document("x" * 11)
        with self.assertRaises(MhtmlGatewayError) as caught:
            extract_tables(document, limits=ParseLimits(max_html_chars=10))
        self.assertEqual(caught.exception.code, ErrorCode.HTML_TOO_LARGE)

    def test_default_root_rejects_non_message_payload_entry(self) -> None:
        """A malformed multipart payload list cannot reach attribute access."""
        message = Message()
        message.set_type("multipart/related")
        message.set_payload(["not-a-message"])
        with self.assertRaises(MhtmlGatewayError) as caught:
            _select_html_root(message, [])
        self.assertEqual(caught.exception.code, ErrorCode.MISSING_HTML_ROOT)


if __name__ == "__main__":
    unittest.main()
