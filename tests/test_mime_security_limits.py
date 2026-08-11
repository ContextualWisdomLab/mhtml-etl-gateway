"""Focused fail-closed MIME security tests."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.mime_parser import parse_mhtml_bytes
from mhtml_etl_gateway.models import ParseLimits
from tests.fixture_factory import make_mhtml


class MimeSecurityLimitTests(unittest.TestCase):
    """Verify decoded-size, empty-root, and identifier ambiguity controls."""

    def test_decoded_html_limit_is_enforced_during_mime_parse(self) -> None:
        """The MIME boundary never returns an over-budget decoded document."""
        source = make_mhtml("<html>0123456789</html>")
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source, limits=ParseLimits(max_html_chars=10))
        self.assertEqual(caught.exception.code, ErrorCode.HTML_TOO_LARGE)

    def test_empty_multipart_related_fails_with_missing_root(self) -> None:
        """A defect-free empty related container cannot reach list index access."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=empty; type="text/html"\r\n'
            b"\r\n--empty--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.MISSING_HTML_ROOT)

    def test_duplicate_content_ids_fail_without_explicit_start(self) -> None:
        """Duplicate normalized identifiers are rejected even on the default-root path."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=dup; type="text/html"\r\n\r\n'
            b"--dup\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Content-ID: <same>\r\n\r\n"
            b"<html>root</html>\r\n"
            b"--dup\r\n"
            b"Content-Type: image/png\r\n"
            b"Content-ID: <same>\r\n\r\n"
            b"PNG\r\n"
            b"--dup--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.AMBIGUOUS_HTML_ROOT)


if __name__ == "__main__":
    unittest.main()
