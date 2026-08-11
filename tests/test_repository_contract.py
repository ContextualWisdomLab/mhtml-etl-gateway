"""Tests for the repository-wide commercial quality contract."""

from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scripts.validate_repository as repository_validator


@contextmanager
def _working_directory(path: Path):
    """Temporarily change the process working directory and always restore it."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _run_validator(root: Path, required_documents: tuple[Path, ...] = ()):
    """Run the repository validator in an isolated synthetic repository."""
    stdout = StringIO()
    with _working_directory(root), patch.object(
        repository_validator,
        "REQUIRED_DOCUMENTS",
        required_documents,
    ), redirect_stdout(stdout):
        return_code = repository_validator.main([])
    return return_code, json.loads(stdout.getvalue())


class RepositoryContractTests(unittest.TestCase):
    """Verify documentation, docstrings, and immutable workflow references."""

    def test_required_document_inventory_is_present(self) -> None:
        """The design, security, test, and operating baseline is complete."""
        self.assertEqual(
            [
                path
                for path in repository_validator.REQUIRED_DOCUMENTS
                if not path.is_file()
            ],
            [],
        )

    def test_public_python_docstrings_include_scripts(self) -> None:
        """Production helper scripts meet the package documentation contract."""
        self.assertEqual(
            repository_validator.missing_public_docstrings(
                (Path("src"), Path("scripts"))
            ),
            [],
        )

    def test_missing_docstring_detector_reports_module_and_symbol(self) -> None:
        """Undocumented production modules and public symbols are both reported."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "undocumented.py"
            source.write_text(
                "def public_function():\n    return 1\n",
                encoding="utf-8",
            )
            self.assertEqual(
                repository_validator.missing_public_docstrings((root,)),
                [str(source), f"{source}:public_function"],
            )

    def test_repository_validator_reports_every_fail_closed_contract(self) -> None:
        """Missing docs, unsafe workflows, artifacts, and placeholders fail together."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github/workflows").mkdir(parents=True)
            (root / "src").mkdir()
            (root / "scripts").mkdir()
            present_document = root / "README.md"
            present_document.write_text(
                "TODO replace this placeholder",
                encoding="utf-8",
            )
            hourly_workflow = root / ".github/workflows/hourly-product-gap.yml"
            hourly_workflow.write_text(
                "name: unsafe\nenv:\n  TOKEN: COPILOT_GITHUB_TOKEN\n",
                encoding="utf-8",
            )
            (root / "customer_export.mhtml").write_bytes(b"sensitive")
            return_code, payload = _run_validator(
                root,
                (Path("README.md"), Path("docs/MISSING.md")),
            )
            self.assertEqual(return_code, 1)
            self.assertEqual(payload["status"], "failed")
            messages = "\n".join(payload["errors"])
            self.assertIn("missing required document", messages)
            self.assertIn("prohibited scheduler credential", messages)
            self.assertIn("does not bind NVIDIA_NIM_API_KEY", messages)
            self.assertIn("does not disable OpenCode session sharing", messages)
            self.assertIn("customer-like MHTML artifact", messages)
            self.assertIn("unresolved placeholder token", messages)

    def test_nested_yaml_workflows_are_scanned_for_unsafe_references(self) -> None:
        """Both nested `.yaml` files and top-level `.yml` files are governed."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            nested = workflows / "nested"
            nested.mkdir(parents=True)
            (workflows / "ignored.yml").mkdir()
            (root / "src").mkdir()
            (root / "scripts").mkdir()
            (workflows / "hourly-product-gap.yml").write_text(
                "env:\n  KEY: ${{ secrets.NVIDIA_NIM_API_KEY }}\n"
                "with:\n  share: false\n",
                encoding="utf-8",
            )
            (nested / "unsafe.yaml").write_text(
                "uses: actions/checkout@v7\n"
                "env:\n  TOKEN: COPILOT_GITHUB_TOKEN\n",
                encoding="utf-8",
            )
            return_code, payload = _run_validator(root)
            self.assertEqual(return_code, 1)
            messages = "\n".join(payload["errors"])
            self.assertIn("mutable action reference", messages)
            self.assertIn("nested/unsafe.yaml", messages)
            self.assertIn("prohibited scheduler credential", messages)

    def test_missing_hourly_workflow_returns_machine_readable_failure(self) -> None:
        """Deleting the scheduler cannot escape as an unstructured file error."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github/workflows").mkdir(parents=True)
            (root / "src").mkdir()
            (root / "scripts").mkdir()
            return_code, payload = _run_validator(root)
            self.assertEqual(return_code, 1)
            self.assertEqual(payload["status"], "failed")
            self.assertIn(
                "missing required workflow: .github/workflows/hourly-product-gap.yml",
                payload["errors"],
            )

    def test_mutable_action_detector_reports_tags(self) -> None:
        """The workflow scanner distinguishes a mutable tag from a full SHA."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text(
                "uses: actions/checkout@v7\n"
                "uses: actions/setup-python@" + "a" * 40 + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                repository_validator.find_mutable_action_references((path,)),
                [(path, "actions/checkout@v7")],
            )

    def test_repository_validator_returns_success_json(self) -> None:
        """The complete checked-in tree passes the deterministic validator."""
        stdout = StringIO()
        with redirect_stdout(stdout):
            return_code = repository_validator.main([])
        self.assertEqual(return_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
