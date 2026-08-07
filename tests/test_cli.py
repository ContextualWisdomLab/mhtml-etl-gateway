"""Tests for the command-line inspection interface."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import runpy
import sys
from pathlib import Path
import tempfile
import unittest

from mhtml_etl_gateway.cli import main
from tests.fixture_factory import make_mhtml


class CliTests(unittest.TestCase):
    """Verify deterministic CLI success and failure output."""

    def test_compact_inspection_json(self) -> None:
        """Compact mode writes one JSON object and returns success."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><td>A</td></tr></table>"))
            stdout = StringIO()
            with redirect_stdout(stdout):
                return_code = main(["inspect", str(path)])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["table_count"], 1)
        self.assertNotIn("\n  ", stdout.getvalue())

    def test_pretty_inspection_json(self) -> None:
        """Pretty mode uses indented UTF-8 JSON."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><td>제목</td></tr></table>"))
            stdout = StringIO()
            with redirect_stdout(stdout):
                return_code = main(["inspect", str(path), "--pretty"])
        self.assertEqual(return_code, 0)
        self.assertNotIn("제목", stdout.getvalue())
        self.assertIn("\n  ", stdout.getvalue())

    def test_header_values_require_explicit_cli_flag(self) -> None:
        """The CLI keeps cell-derived names private unless the operator opts in."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><td>MANDT</td></tr></table>"))
            default_stdout = StringIO()
            privileged_stdout = StringIO()
            with redirect_stdout(default_stdout):
                default_code = main(["inspect", str(path)])
            with redirect_stdout(privileged_stdout):
                privileged_code = main(["inspect", str(path), "--include-header-values"])
        self.assertEqual(default_code, 0)
        self.assertEqual(privileged_code, 0)
        self.assertNotIn("MANDT", default_stdout.getvalue())
        self.assertIn("MANDT", privileged_stdout.getvalue())

    def test_expected_failure_is_json_on_stderr(self) -> None:
        """Missing files fail with a stable JSON error and status 2."""
        stderr = StringIO()
        with redirect_stderr(stderr):
            return_code = main(["inspect", "/missing/source.mhtml"])
        payload = json.loads(stderr.getvalue())
        self.assertEqual(return_code, 2)
        self.assertEqual(payload["error_code"], "source_read_failed")
        self.assertNotIn("/missing/source.mhtml", payload["message"])

    def test_argument_parser_rejects_missing_command(self) -> None:
        """Argparse retains its conventional status 2 for malformed invocation."""
        with self.assertRaises(SystemExit) as caught:
            main([])
        self.assertEqual(caught.exception.code, 2)

    def test_module_entrypoint_returns_cli_status(self) -> None:
        """The package module delegates to the same CLI implementation."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><td>A</td></tr></table>"))
            previous_argv = sys.argv
            stdout = StringIO()
            try:
                sys.argv = ["mhtml-etl-gateway", "inspect", str(path)]
                with redirect_stdout(stdout), self.assertRaises(SystemExit) as caught:
                    runpy.run_module("mhtml_etl_gateway", run_name="__main__")
            finally:
                sys.argv = previous_argv
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["table_count"], 1)


if __name__ == "__main__":
    unittest.main()
