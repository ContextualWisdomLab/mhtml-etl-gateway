"""Tests for stable error contracts."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway import __version__
from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError


class ErrorContractTests(unittest.TestCase):
    """Verify externally visible error behavior."""

    def test_error_codes_are_stable_strings(self) -> None:
        """Error values remain machine-readable lowercase identifiers."""
        self.assertEqual(ErrorCode.INVALID_ARGUMENT.value, "invalid_argument")
        self.assertEqual(ErrorCode.SOURCE_TOO_LARGE.value, "source_too_large")
        self.assertEqual(ErrorCode.NESTED_TABLE.value, "nested_table")

    def test_exception_exposes_only_fixed_code_message_pair(self) -> None:
        """The exception discards caller detail and exposes approved-safe text."""
        error = MhtmlGatewayError(
            ErrorCode.MISSING_HTML_ROOT,
            "attacker-selected identifier",
        )
        self.assertEqual(error.code, ErrorCode.MISSING_HTML_ROOT)
        self.assertEqual(error.message, "MHTML input has no valid HTML root")
        self.assertEqual(
            str(error),
            "missing_html_root: MHTML input has no valid HTML root",
        )
        self.assertNotIn("attacker", str(error))

    def test_package_version_is_semantic(self) -> None:
        """The package exports the current release's semantic version."""
        self.assertEqual(__version__, "0.3.2")


if __name__ == "__main__":
    unittest.main()
