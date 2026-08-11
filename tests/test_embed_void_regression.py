"""Regression coverage for void embedded-resource elements."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.html_tables import extract_tables
from mhtml_etl_gateway.mime_parser import parse_mhtml_bytes
from tests.fixture_factory import make_mhtml


class EmbedVoidRegressionTests(unittest.TestCase):
    """Verify that a valid void embed element does not suppress later text."""

    def test_embed_without_closing_tag_preserves_following_cell_text(self) -> None:
        """Text following a void embed remains part of the logical cell."""
        source = make_mhtml(
            "<table><tr><td>before<embed src='asset.bin'>after</td></tr></table>"
        )
        table = extract_tables(parse_mhtml_bytes(source))[0]
        self.assertEqual(table.headers, ("beforeafter",))


if __name__ == "__main__":
    unittest.main()
