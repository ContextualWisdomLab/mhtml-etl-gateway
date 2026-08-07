"""Tests for the repository-wide commercial quality contract."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scripts.validate_repository as repository_validator
from scripts.validate_repository import (
    REQUIRED_DOCUMENTS,
    find_mutable_action_references,
    main,
    missing_public_docstrings,
)


class RepositoryContractTests(unittest.TestCase):
    """Verify documentation, docstrings, and immutable workflow references."""

    def test_required_document_inventory_is_present(self) -> None:
        """The design, security, test, and operating baseline is complete."""
        self.assertEqual([path for path in REQUIRED_DOCUMENTS if not path.is_file()], [])

    def test_public_python_docstrings_include_scripts(self) -> None:
        """Production helper scripts meet the same documentation contract as the package."""
        self.assertEqual(missing_public_docstrings((Path("src"), Path("scripts"))), [])

    def test_missing_docstring_detector_reports_module_and_symbol(self) -> None:
        """Undocumented production modules and public symbols are both reported."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "undocumented.py"
            source.write_text("def public_function():\n    return 1\n", encoding="utf-8")
            self.assertEqual(
                missing_public_docstrings((root,)),
                [str(source), f"{source}:public_function"],
            )

    def test_repository_validator_reports_every_fail_closed_contract(self) -> None:
        """Missing docs, unsafe workflows, source artifacts, and placeholders fail together."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github/workflows").mkdir(parents=True)
            (root / "src").mkdir()
            (root / "scripts").mkdir()
            present_document = root / "README.md"
            present_document.write_text("TODO replace this placeholder", encoding="utf-8")
            hourly_workflow = root / ".github/workflows/hourly-product-gap.yml"
            hourly_workflow.write_text(
                "name: unsafe\nenv:\n  TOKEN: COPILOT_GITHUB_TOKEN\n",
                encoding="utf-8",
            )
            (root / "customer_export.mhtml").write_bytes(b"sensitive")
            stdout = StringIO()
            previous = Path.cwd()
            try:
                import os

                os.chdir(root)
                with patch.object(
                    repository_validator,
                    "REQUIRED_DOCUMENTS",
                    (Path("README.md"), Path("docs/MISSING.md")),
                ), redirect_stdout(stdout):
                    return_code = main([])
            finally:
                os.chdir(previous)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(return_code, 1)
            self.assertEqual(payload["status"], "failed")
            messages = "\n".join(payload["errors"])
            self.assertIn("missing required document", messages)
            self.assertIn("prohibited scheduler credential", messages)
            self.assertIn("does not bind NVIDIA_NIM_API_KEY", messages)
            self.assertIn("does not disable OpenCode session sharing", messages)
            self.assertIn("customer-like MHTML artifact", messages)
            self.assertIn("unresolved placeholder token", messages)

    def test_mutable_action_detector_reports_tags(self) -> None:
        """The workflow scanner distinguishes a mutable tag from a full SHA."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text(
                "uses: actions/checkout@v7\nuses: actions/setup-python@" + "a" * 40 + "\n",
                encoding="utf-8",
            )
            self.assertEqual(find_mutable_action_references((path,)), [(path, "actions/checkout@v7")])

    def test_repository_validator_returns_success_json(self) -> None:
        """The complete checked-in tree passes the deterministic validator."""
        stdout = StringIO()
        with redirect_stdout(stdout):
            return_code = main([])
        self.assertEqual(return_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
