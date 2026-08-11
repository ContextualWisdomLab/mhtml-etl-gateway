"""Regression tests for CLI argument and inspection error boundaries."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mhtml_etl_gateway.cli import main
from tests.fixture_factory import make_mhtml


class CliErrorBoundaryTests(unittest.TestCase):
    """Keep raw argument validation separate from inspection-domain failures."""

    def test_unexpected_inspection_value_error_is_not_reclassified(self) -> None:
        """A programming defect cannot masquerade as a user argument failure."""
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.mhtml"
            source_path.write_bytes(make_mhtml("<table></table>"))
            with patch(
                "mhtml_etl_gateway.cli.inspect_mhtml_file",
                side_effect=ValueError("unexpected inspection defect"),
            ):
                with self.assertRaisesRegex(ValueError, "unexpected inspection defect"):
                    main(["inspect", str(source_path)])


if __name__ == "__main__":
    unittest.main()
