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
        """Pretty mode uses indented UTF-8 JSON without source values."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><td>제목</td></tr></table>"))
            stdout = StringIO()
            with redirect_stdout(stdout):
                return_code = main(["inspect", str(path), "--pretty"])
        self.assertEqual(return_code, 0)
        self.assertNotIn("제목", stdout.getvalue())
        self.assertIn("\n  ", stdout.getvalue())

    def test_schema_proposal_json_is_value_free(self) -> None:
        """Proposal CLI output contains review evidence but no protected values."""
        html = """
        <table>
          <tr><th>DUEDT</th><th>KUNNR</th><th>TITLE</th></tr>
          <tr><td>20250131</td><td>0012345678</td><td>고객 문의</td></tr>
        </table>
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "customer-private.mhtml"
            path.write_bytes(make_mhtml(html))
            stdout = StringIO()
            with redirect_stdout(stdout):
                return_code = main(["propose", str(path)])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(return_code, 0)
        self.assertRegex(
            payload["schema_proposal_id"], r"^schema_proposal_[0-9a-f]{32}$"
        )
        self.assertEqual(payload["columns"][0]["target_column_name"], "due_date")
        self.assertEqual(payload["columns"][0]["proposed_type"], "date")
        rendered = stdout.getvalue()
        for protected in ("DUEDT", "KUNNR", "0012345678", "고객 문의"):
            self.assertNotIn(protected, rendered)

    def test_pretty_schema_proposal_json_and_fixed_failure(self) -> None:
        """Pretty proposals work and malformed sources use a fixed error contract."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><th>A</th></tr></table>"))
            stdout = StringIO()
            with redirect_stdout(stdout):
                return_code = main(["propose", str(path), "--pretty"])
            self.assertEqual(return_code, 0)
            self.assertIn("\n  ", stdout.getvalue())

            malformed = Path(directory) / "malformed.mhtml"
            malformed.write_bytes(b"not an MHTML document")
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = main(["propose", str(malformed)])

            payload = json.loads(stderr.getvalue())
            self.assertEqual(return_code, 2)
            self.assertEqual(payload["error_code"], "invalid_mime")
            self.assertNotIn("not an MHTML document", payload["message"])

            no_table = Path(directory) / "no-table.mhtml"
            no_table.write_bytes(make_mhtml("<html><body>no table</body></html>"))
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = main(["propose", str(no_table)])

        payload = json.loads(stderr.getvalue())
        self.assertEqual(return_code, 2)
        self.assertEqual(payload["error_code"], "schema_proposal_failed")

    def test_schema_proposal_missing_file_is_fixed_json(self) -> None:
        """A missing proposal source never reflects the operator path."""
        stderr = StringIO()
        with redirect_stderr(stderr):
            return_code = main(["propose", "/missing/private-source.mhtml"])
        payload = json.loads(stderr.getvalue())
        self.assertEqual(return_code, 2)
        self.assertEqual(payload["error_code"], "source_read_failed")
        self.assertNotIn("/missing/private-source.mhtml", payload["message"])

    def test_schema_proposal_invalid_source_limit_is_fixed_json(self) -> None:
        """Proposal resource limits use the shared invalid-argument contract."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><th>A</th></tr></table>"))
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = main(["propose", str(path), "--max-source-bytes", "0"])
            payload = json.loads(stderr.getvalue())
            self.assertEqual(return_code, 2)
            self.assertEqual(payload["error_code"], "invalid_argument")

            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = main(["propose", str(path), "--max-source-bytes", "1"])
            payload = json.loads(stderr.getvalue())
            self.assertEqual(return_code, 2)
            self.assertEqual(payload["error_code"], "source_too_large")

    def test_expected_failure_is_json_on_stderr(self) -> None:
        """Missing files fail with a fixed JSON error and status 2."""
        stderr = StringIO()
        with redirect_stderr(stderr):
            return_code = main(["inspect", "/missing/source.mhtml"])
        payload = json.loads(stderr.getvalue())
        self.assertEqual(return_code, 2)
        self.assertEqual(payload["error_code"], "source_read_failed")
        self.assertNotIn("/missing/source.mhtml", payload["message"])

    def test_argument_parser_failure_is_json(self) -> None:
        """A missing command is returned through the public JSON contract."""
        stderr = StringIO()
        with redirect_stderr(stderr):
            return_code = main([])
        self.assertEqual(return_code, 2)
        self.assertEqual(
            json.loads(stderr.getvalue())["error_code"], "invalid_argument"
        )

    def test_invalid_positive_limit_is_json(self) -> None:
        """A non-positive resource budget uses the same fixed argument error."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table></table>"))
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = main(["inspect", str(path), "--max-source-bytes", "0"])
        self.assertEqual(return_code, 2)
        self.assertEqual(
            json.loads(stderr.getvalue())["error_code"], "invalid_argument"
        )

    def test_removed_header_disclosure_flag_is_json_error(self) -> None:
        """The former header-value option is rejected without usage reflection."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(make_mhtml("<table><tr><th>A</th></tr></table>"))
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = main(["inspect", str(path), "--include-header-values"])
        self.assertEqual(return_code, 2)
        self.assertEqual(
            json.loads(stderr.getvalue())["error_code"], "invalid_argument"
        )

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
