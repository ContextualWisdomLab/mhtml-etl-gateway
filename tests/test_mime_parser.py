"""Tests for bounded MHTML MIME parsing."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from email.message import Message

from mhtml_etl_gateway.mime_parser import (
    _raw_payload_bytes,
    parse_mhtml_bytes,
    parse_mhtml_file,
)
from mhtml_etl_gateway.models import ParseLimits
from tests.fixture_factory import make_mhtml, make_standalone_html


class MimeParserTests(unittest.TestCase):
    """Verify root resolution, decoding, and input bounds."""

    def test_start_parameter_selects_named_root(self) -> None:
        """RFC 2387 start selects the matching Content-ID over a decoy."""
        source = make_mhtml(
            "<html><table><tr><td>ROOT</td></tr></table></html>",
            include_decoy=True,
        )
        document = parse_mhtml_bytes(source)
        self.assertIn("ROOT", document.html_text)
        self.assertNotIn("DECOY", document.html_text)
        self.assertEqual(document.root_content_id, "root-part")

    def test_first_body_part_is_root_when_start_is_absent(self) -> None:
        """The first body part becomes the HTML root when start is absent."""
        source = make_mhtml("<html>ROOT</html>", start=None)
        document = parse_mhtml_bytes(source)
        self.assertIn("ROOT", document.html_text)

    def test_no_start_never_skips_a_non_html_default_root(self) -> None:
        """RFC 2387 default-root order cannot be rewritten to a later HTML part."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"\r\n\r\n'
            b"--abc\r\nContent-Type: text/plain\r\n\r\nnot-root-html\r\n"
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html>later</html>\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.MISSING_HTML_ROOT)

    def test_standalone_html_is_supported(self) -> None:
        """A single text/html MIME entity is a valid input."""
        document = parse_mhtml_bytes(make_standalone_html("<html>단독</html>"))
        self.assertIn("단독", document.html_text)
        self.assertEqual(document.root_content_location, "file:///standalone.html")

    def test_source_size_is_enforced_before_parse(self) -> None:
        """Oversized input fails with the stable source limit code."""
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(b"x" * 10, limits=ParseLimits(max_source_bytes=9))
        self.assertEqual(caught.exception.code, ErrorCode.SOURCE_TOO_LARGE)

    def test_mime_part_count_is_bounded(self) -> None:
        """Multipart messages cannot exceed the configured leaf-part budget."""
        source = make_mhtml("<html>root</html>", include_decoy=True)
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source, limits=ParseLimits(max_mime_parts=1))
        self.assertEqual(caught.exception.code, ErrorCode.TOO_MANY_MIME_PARTS)

    def test_mime_parser_defects_fail_closed(self) -> None:
        """Malformed multipart boundaries cannot be accepted by tolerant parsing."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/related; boundary=abc\r\n\r\n"
            b"--abc\r\nContent-Type: text/html\r\n\r\n<html>root</html>"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)

    def test_duplicate_security_critical_headers_are_rejected(self) -> None:
        """Duplicate MIME headers cannot steer different parser interpretations."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Content-Type: customer/secret\r\n\r\n"
            b"<html>root</html>"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)
        self.assertNotIn("customer/secret", caught.exception.message)

    def test_duplicate_root_content_location_is_rejected_without_reflection(
        self,
    ) -> None:
        """Multiple source labels fail closed instead of leaking or choosing one."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Content-Location: file:///private/customer-one.html\r\n"
            b"Content-Location: file:///private/customer-two.html\r\n\r\n"
            b"<html>root</html>"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)
        self.assertNotIn("customer-one", caught.exception.message)

    def test_non_mhtml_message_is_rejected(self) -> None:
        """Plain text cannot be treated as an HTML root."""
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(b"Content-Type: text/plain\r\n\r\nhello")
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)

    def test_start_identifier_must_resolve(self) -> None:
        """An explicit but missing root identifier fails closed."""
        source = make_mhtml("<html>root</html>", start="customer-secret-missing")
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.MISSING_HTML_ROOT)
        self.assertNotIn("customer-secret", caught.exception.message)

    def test_unknown_charset_is_rejected(self) -> None:
        """Unknown declared character sets do not silently fall back."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: text/html; charset=x-not-real\r\n\r\n"
            b"<html>test</html>"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.UNKNOWN_CHARSET)
        self.assertNotIn("x-not-real", caught.exception.message)

    def test_invalid_declared_encoding_is_rejected(self) -> None:
        """Bytes that do not match the declared charset fail decoding."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n\r\n"
            b"<html>\xff</html>"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.HTML_DECODE_FAILED)

    def test_utf16_bom_is_detected_without_charset(self) -> None:
        """A BOM provides deterministic decoding when charset is absent."""
        body = "<html>유니코드</html>".encode("utf-16")
        source = b"MIME-Version: 1.0\r\nContent-Type: text/html\r\n\r\n" + body
        document = parse_mhtml_bytes(source)
        self.assertIn("유니코드", document.html_text)

    def test_unknown_transfer_encoding_records_diagnostic(self) -> None:
        """Enterprise identity encodings are accepted but explicitly diagnosed."""
        source = make_mhtml(
            "<html>root</html>",
            content_transfer_encoding="text/html",
        )
        document = parse_mhtml_bytes(source)
        self.assertIn(
            "identity_transfer_encoding",
            [diagnostic.code for diagnostic in document.diagnostics],
        )
        self.assertNotIn("text/html", repr(document.diagnostics))

    def test_missing_related_type_is_accepted_with_diagnostic(self) -> None:
        """A known enterprise omission remains usable but never silently conformant."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/related; boundary=abc\r\n\r\n"
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html>root</html>\r\n--abc--\r\n"
        )
        document = parse_mhtml_bytes(source)
        self.assertIn("root", document.html_text)
        self.assertIn(
            "missing_related_type", [item.code for item in document.diagnostics]
        )

    def test_related_type_must_match_selected_root_without_reflection(self) -> None:
        """A contradictory compound-object type fails closed without echoing it."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="customer/secret"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html>root</html>\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)
        self.assertNotIn("customer/secret", caught.exception.message)

    def test_duplicate_related_parameters_are_rejected(self) -> None:
        """Duplicate root-selection parameters fail before a parser can choose one."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"; start="<root>"; start="<other>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\n\r\n<html>root</html>\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)

    def test_semicolon_inside_quoted_parameter_is_not_a_duplicate(self) -> None:
        """Quoted parameter content cannot manufacture a second parameter name."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"; start="<root;start=fake>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root;start=fake>\r\n\r\n<html>root</html>\r\n--abc--\r\n"
        )
        self.assertIn("root", parse_mhtml_bytes(source).html_text)

    def test_escaped_quote_in_noncritical_parameter_cannot_split_parameters(
        self,
    ) -> None:
        """An escaped quote keeps semicolons inside a quoted parameter value."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"; '
            b'x-note="a\\";start=fake"; start="<root>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\n\r\n<html>root</html>\r\n--abc--\r\n"
        )
        self.assertIn("root", parse_mhtml_bytes(source).html_text)

    def test_nested_content_type_comments_do_not_split_parameters(self) -> None:
        """Nested MIME comments remain outside the security-critical parameter set."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/related; boundary=abc (outer (inner)); "
            b'type="text/html"; start="<root>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\n\r\n<html>root</html>\r\n--abc--\r\n"
        )
        self.assertIn("root", parse_mhtml_bytes(source).html_text)

    def test_malformed_content_type_parameter_is_rejected(self) -> None:
        """Content-Type parser defects that affect root selection fail closed."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"; '
            b'orphan; start="<root>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\n\r\n<html>root</html>\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)
        self.assertNotIn("orphan", caught.exception.message)

    def test_multipart_without_html_is_rejected(self) -> None:
        """A related message containing only non-HTML parts has no valid root."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/related; boundary=abc\r\n\r\n"
            b"--abc\r\nContent-Type: text/plain\r\n\r\nplain\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.MISSING_HTML_ROOT)

    def test_duplicate_root_content_ids_are_rejected(self) -> None:
        """An explicit start identifier cannot resolve ambiguously."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; start="<root>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\n\r\n<html>one</html>\r\n"
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\n\r\n<html>two</html>\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.AMBIGUOUS_HTML_ROOT)
        self.assertNotIn("root", caught.exception.message)

    def test_start_identifier_is_ambiguous_across_all_media_types(self) -> None:
        """Duplicate Content-IDs cannot be hidden by filtering to HTML first."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"; start="<root>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\n\r\n<html>one</html>\r\n"
            b"--abc\r\nContent-Type: image/png\r\nContent-ID: <root>\r\n\r\nPNG\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.AMBIGUOUS_HTML_ROOT)

    def test_start_identifier_must_point_to_html(self) -> None:
        """An explicit root that resolves only to another media type is rejected."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"; start="<root>"\r\n\r\n'
            b"--abc\r\nContent-Type: text/plain\r\nContent-ID: <root>\r\n\r\nplain\r\n"
            b"--abc\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <later>\r\n\r\n<html>later</html>\r\n--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.MISSING_HTML_ROOT)

    def test_utf8_is_default_without_charset_or_bom(self) -> None:
        """Charset-free HTML uses strict UTF-8 as the deterministic default."""
        source = (
            b"MIME-Version: 1.0\r\nContent-Type: text/html\r\n\r\n"
            + "<html>기본</html>".encode("utf-8")
        )
        self.assertIn("기본", parse_mhtml_bytes(source).html_text)

    def test_non_bytes_argument_is_rejected_as_invalid_mime(self) -> None:
        """Runtime type misuse cannot escape as an unstructured exception."""
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes("not bytes")  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, ErrorCode.INVALID_MIME)

    def test_parse_file_reads_existing_file(self) -> None:
        """The file API delegates to the byte parser."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mhtml"
            path.write_bytes(make_mhtml("<html>file</html>"))
            self.assertIn("file", parse_mhtml_file(path).html_text)

    def test_parse_file_rejects_missing_path(self) -> None:
        """A missing file is reported as a stable source-read error."""
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_file("/definitely/missing/export.mhtml")
        self.assertEqual(caught.exception.code, ErrorCode.SOURCE_READ_FAILED)
        self.assertNotIn("/definitely/missing/export.mhtml", caught.exception.message)

    def test_selected_part_without_byte_payload_is_rejected(self) -> None:
        """A structurally invalid selected part cannot masquerade as HTML bytes."""
        part = Message()
        part.set_payload([Message()])
        with self.assertRaises(MhtmlGatewayError) as caught:
            _raw_payload_bytes(part)
        self.assertEqual(caught.exception.code, ErrorCode.HTML_DECODE_FAILED)


if __name__ == "__main__":
    unittest.main()
