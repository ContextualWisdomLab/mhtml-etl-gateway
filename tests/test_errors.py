"""Tests for stable error contracts."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway import __version__
from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError


class ErrorContractTests(unittest.TestCase):
    """Verify externally visible error behavior."""

    def test_error_codes_are_stable_strings(self) -> None:
        """Error values remain machine-readable lowercase identifiers."""
        self.assertEqual(ErrorCode.SOURCE_TOO_LARGE.value, "source_too_large")
        self.assertEqual(ErrorCode.NESTED_TABLE.value, "nested_table")

    def test_exception_exposes_code_and_message(self) -> None:
        """The exception retains a stable code and human-readable message."""
        error = MhtmlGatewayError(ErrorCode.MISSING_HTML_ROOT, "HTML root missing")
        self.assertEqual(error.code, ErrorCode.MISSING_HTML_ROOT)
        self.assertEqual(error.message, "HTML root missing")
        self.assertEqual(str(error), "missing_html_root: HTML root missing")

    def test_package_version_is_semantic(self) -> None:
        """The package exports its initial semantic version."""
        self.assertEqual(__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
