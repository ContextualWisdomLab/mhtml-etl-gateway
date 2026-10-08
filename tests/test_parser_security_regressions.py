"""Security regressions for MIME root selection and inert HTML content."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.html_tables import extract_tables
from mhtml_etl_gateway.mime_parser import parse_mhtml_bytes
from mhtml_etl_gateway.models import MhtmlDocument


class ParserSecurityRegressionTests(unittest.TestCase):
    """Prove fail-closed behavior for previously reachable parser ambiguities."""

    def test_default_root_is_first_direct_body_part_not_first_leaf(self) -> None:
        """A nested HTML leaf cannot replace a non-HTML direct default root."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=outer; type="text/html"\r\n\r\n'
            b"--outer\r\n"
            b"Content-Type: multipart/alternative; boundary=inner\r\n\r\n"
            b"--inner\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n\r\n"
            b"<html>nested</html>\r\n"
            b"--inner--\r\n"
            b"--outer\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n\r\n"
            b"<html>later</html>\r\n"
            b"--outer--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.MISSING_HTML_ROOT)

    def test_start_duplicate_is_ambiguous_before_media_type_validation(self) -> None:
        """Duplicate Content-IDs stay ambiguous regardless of part ordering."""
        source = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary=abc; type="text/html"; '
            b'start="<root>"\r\n\r\n'
            b"--abc\r\n"
            b"Content-Type: image/png\r\n"
            b"Content-ID: <root>\r\n\r\n"
            b"PNG\r\n"
            b"--abc\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Content-ID: <root>\r\n\r\n"
            b"<html>root</html>\r\n"
            b"--abc--\r\n"
        )
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(source)
        self.assertEqual(caught.exception.code, ErrorCode.AMBIGUOUS_HTML_ROOT)

    def test_mismatched_suppressed_end_tag_cannot_escape_outer_boundary(self) -> None:
        """An extra closing tag cannot expose text still enclosed by a template."""
        document = MhtmlDocument(
            html_text=(
                "<table><tr><td>visible"
                "<template><style></style></style>secret</template>"
                "after</td></tr></table>"
            ),
            root_content_type="text/html",
            root_content_location=None,
            root_content_id=None,
            diagnostics=(),
        )
        table = extract_tables(document)[0]
        self.assertEqual(table.headers, ("visibleafter",))
        self.assertNotIn("secret", table.headers[0])

    def test_unrelated_elements_outside_tables_are_ignored(self) -> None:
        """Ordinary document elements outside tables do not create structure."""
        document = MhtmlDocument(
            html_text=("<div>outside</div>" "<table><tr><td>A</td></tr></table>"),
            root_content_type="text/html",
            root_content_location=None,
            root_content_id=None,
            diagnostics=(),
        )
        table = extract_tables(document)[0]
        self.assertEqual(table.headers, ("A",))

    @staticmethod
    def _nested_related_source(depth: int) -> bytes:
        """Build a deeply nested MIME entity with one HTML leaf."""
        chunks: list[str] = []
        for index in range(depth):
            boundary = f"nested_{index}"
            chunks.append(
                "MIME-Version: 1.0\r\n"
                f'Content-Type: multipart/related; boundary={boundary}; type="text/html"\r\n\r\n'
                f"--{boundary}\r\n"
            )
        chunks.append(
            "Content-Type: text/html; charset=utf-8\r\n\r\n" "<html>root</html>\r\n"
        )
        for index in reversed(range(depth)):
            chunks.append(f"--nested_{index}--\r\n")
        return "".join(chunks).encode("ascii")

    def test_mime_depth_budget_rejects_nested_entities(self) -> None:
        """Nested multipart entities consume an explicit depth budget."""
        from mhtml_etl_gateway.models import ParseLimits

        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(
                self._nested_related_source(4),
                limits=ParseLimits(max_mime_depth=2),
            )

        self.assertEqual(caught.exception.code, ErrorCode.MIME_NESTING_TOO_DEEP)

    def test_extreme_mime_nesting_never_escapes_as_recursion_error(self) -> None:
        """Parser recursion exhaustion is converted to a stable fail-closed error."""
        with self.assertRaises(MhtmlGatewayError) as caught:
            parse_mhtml_bytes(self._nested_related_source(2_000))

        self.assertEqual(caught.exception.code, ErrorCode.MIME_NESTING_TOO_DEEP)


if __name__ == "__main__":
    unittest.main()
