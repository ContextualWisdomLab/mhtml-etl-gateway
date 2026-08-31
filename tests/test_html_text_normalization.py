"""Regression tests for HTML cell text normalization."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.html_tables import _normalize_text


class HtmlTextNormalizationTests(unittest.TestCase):
    """Cover fast-path and line-break contracts for cell text normalization."""

    def test_empty_and_whitespace_only_fragments_normalize_to_empty(self) -> None:
        """Empty, ASCII, and Unicode whitespace all normalize to empty text."""
        cases = (
            [],
            [""],
            [" \t\f\v"],
            ["\u2003"],
        )
        for fragments in cases:
            with self.subTest(fragments=fragments):
                self.assertEqual(_normalize_text(fragments), "")

    def test_carriage_return_variants_preserve_line_breaks(self) -> None:
        """CRLF and CR separators normalize to explicit LF line breaks."""
        self.assertEqual(
            _normalize_text(["first\r\nsecond\rthird"]),
            "first\nsecond\nthird",
        )

    def test_non_whitespace_uses_full_normalization_path(self) -> None:
        """Visible text still collapses horizontal whitespace without losing LF."""
        self.assertEqual(
            _normalize_text([" A\t B \n C "]),
            "A B\nC",
        )


if __name__ == "__main__":
    unittest.main()
