"""Tests for the bounded hourly product-development eligibility gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.hourly_product_gap import (
    GateDecision,
    evaluate_gate,
    load_records,
    main,
)


class HourlyProductGapTests(unittest.TestCase):
    """Verify single-flight and secret-availability decisions."""

    def test_load_records_flattens_paginated_api_arrays(self) -> None:
        """GitHub CLI --slurp output is flattened into individual records."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            path.write_text(json.dumps([[{"number": 1}], [{"number": 2}]]), encoding="utf-8")
            self.assertEqual([item["number"] for item in load_records(path)], [1, 2])

    def test_load_records_rejects_non_array_json(self) -> None:
        """Malformed preflight evidence fails closed."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON array"):
                load_records(path)

    def test_load_records_accepts_flat_record_arrays(self) -> None:
        """A non-paginated GitHub response remains a flat record list."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            path.write_text(json.dumps([{"number": 3}]), encoding="utf-8")
            self.assertEqual(load_records(path), [{"number": 3}])

    def test_load_records_rejects_non_object_records(self) -> None:
        """A scalar nested in GitHub evidence fails closed."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            path.write_text(json.dumps([["invalid"]]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be an object"):
                load_records(path)

    def test_gate_requires_nvidia_key(self) -> None:
        """The scheduler cannot run a model without NVIDIA NIM credentials."""
        self.assertEqual(
            evaluate_gate([], [], nvidia_key_configured=False),
            GateDecision(False, "nvidia_nim_api_key_unconfigured"),
        )

    def test_gate_stops_when_pull_request_is_open(self) -> None:
        """Any open pull request makes the product-development loop single-flight."""
        self.assertEqual(
            evaluate_gate([{"number": 4}], [], nvidia_key_configured=True),
            GateDecision(False, "open_pull_request_exists"),
        )

    def test_gate_resumes_one_active_non_pr_issue(self) -> None:
        """One durable agent-task issue is resumed instead of duplicated."""
        issues = [{"number": 7, "labels": [{"name": "agent-task"}]}]
        self.assertEqual(
            evaluate_gate([], issues, nvidia_key_configured=True),
            GateDecision(True, "resume_agent_task", task_number=7),
        )

    def test_gate_rejects_malformed_durable_task_number(self) -> None:
        """An agent-task issue without a positive integer number fails closed."""
        issues = [{"number": "7", "labels": [{"name": "agent-task"}]}]
        self.assertEqual(
            evaluate_gate([], issues, nvidia_key_configured=True),
            GateDecision(False, "agent_task_metadata_invalid"),
        )

    def test_gate_stops_for_multiple_active_agent_tasks(self) -> None:
        """Ambiguous durable task state fails closed for operator review."""
        issues = [
            {"number": 7, "labels": [{"name": "agent-task"}]},
            {"number": 8, "labels": [{"name": "agent-task"}]},
        ]
        self.assertEqual(
            evaluate_gate([], issues, nvidia_key_configured=True),
            GateDecision(False, "multiple_active_agent_tasks"),
        )

    def test_gate_ignores_malformed_and_unrelated_labels(self) -> None:
        """Malformed or unrelated issue labels cannot manufacture active work."""
        issues = [
            {"number": 7, "labels": "agent-task"},
            {"number": 8, "labels": ["agent-task", {"name": "documentation"}]},
        ]
        self.assertEqual(
            evaluate_gate([], issues, nvidia_key_configured=True),
            GateDecision(True, "create_agent_task"),
        )

    def test_gate_ignores_pr_shaped_issue_records(self) -> None:
        """The GitHub issues endpoint's PR records are not counted twice."""
        issues = [{"number": 7, "pull_request": {"url": "https://example.invalid"}}]
        self.assertEqual(
            evaluate_gate([], issues, nvidia_key_configured=True),
            GateDecision(True, "create_agent_task"),
        )

    def test_main_writes_github_output_and_json(self) -> None:
        """The CLI emits both human evidence and a GitHub step output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pulls = root / "pulls.json"
            issues = root / "issues.json"
            output = root / "github-output.txt"
            pulls.write_text("[]", encoding="utf-8")
            issues.write_text("[]", encoding="utf-8")
            with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "configured"}, clear=False):
                return_code = main(
                    [
                        "--pull-requests-json",
                        str(pulls),
                        "--issues-json",
                        str(issues),
                        "--github-output",
                        str(output),
                    ]
                )
            self.assertEqual(return_code, 0)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "eligible=true\nreason=create_agent_task\ntask_number=\n",
            )


if __name__ == "__main__":
    unittest.main()
