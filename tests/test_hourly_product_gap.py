"""Tests for the bounded hourly maintenance and product-development gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.hourly_product_gap import (
    GateDecision,
    _output_value,
    evaluate_gate,
    load_records,
    main,
)

_REPOSITORY = "ContextualWisdomLab/mhtml-etl-gateway"


def pull_request(
    number: int,
    *,
    sha: str | None = None,
    head_repository: str = _REPOSITORY,
    head_ref: str | None = None,
    base_ref: str = "main",
    base_repository: str = _REPOSITORY,
) -> dict[str, object]:
    """Return realistic GitHub pull-request metadata for scheduler tests."""
    return {
        "number": number,
        "state": "open",
        "head": {
            "sha": sha or f"{number:040x}",
            "ref": head_ref or f"agent/pr-{number}",
            "repo": {"full_name": head_repository},
        },
        "base": {
            "ref": base_ref,
            "repo": {"full_name": base_repository},
        },
    }


class HourlyProductGapTests(unittest.TestCase):
    """Verify exact-head maintenance, single-flight, and credential decisions."""

    def test_load_records_flattens_paginated_api_arrays(self) -> None:
        """GitHub CLI ``--slurp`` pages are flattened into individual records."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            path.write_text(
                json.dumps([[{"number": 1}], [{"number": 2}]]),
                encoding="utf-8",
            )
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

    def test_gate_requires_repository_identity(self) -> None:
        """The gate cannot infer same-repository write authority without identity."""
        self.assertEqual(
            evaluate_gate(
                [],
                [],
                nvidia_key_configured=True,
                repository_full_name="",
            ),
            GateDecision(False, "blocked", "repository_metadata_unconfigured"),
        )

    def test_gate_requires_nvidia_key_before_any_agent_mode(self) -> None:
        """Neither PR repair nor product work runs without the approved credential."""
        self.assertEqual(
            evaluate_gate(
                [pull_request(4)],
                [],
                nvidia_key_configured=False,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(False, "blocked", "nvidia_nim_api_key_unconfigured"),
        )

    def test_gate_selects_oldest_open_pr_for_exact_head_maintenance(self) -> None:
        """An open PR is actionable work rather than a blanket scheduler no-op."""
        selected = pull_request(4, sha="a" * 40, head_ref="agent/four")
        decision = evaluate_gate(
            [pull_request(9, sha="b" * 40), selected],
            [],
            nvidia_key_configured=True,
            repository_full_name=_REPOSITORY,
        )
        self.assertEqual(
            decision,
            GateDecision(
                True,
                "maintain_pull_request",
                "open_pull_request_selected",
                pull_request_number=4,
                pull_request_head_sha="a" * 40,
                pull_request_head_ref="agent/four",
                pull_request_base_ref="main",
                pull_request_writable=True,
                open_pull_request_count=2,
            ),
        )

    def test_factory_sha_remains_exactly_40_hex_characters(self) -> None:
        """PR numbers above hexadecimal digit boundaries keep valid test heads."""
        generated = pull_request(16)["head"]
        self.assertEqual(len(generated["sha"]), 40)  # type: ignore[index]

    def test_gate_marks_fork_pr_read_only_instead_of_assuming_write_access(
        self,
    ) -> None:
        """A fork PR can be diagnosed but cannot be treated as a writable lease."""
        decision = evaluate_gate(
            [pull_request(5, head_repository="outside/fork")],
            [],
            nvidia_key_configured=True,
            repository_full_name=_REPOSITORY,
        )
        self.assertEqual(decision.mode, "maintain_pull_request")
        self.assertFalse(decision.pull_request_writable)
        self.assertEqual(decision.pull_request_number, 5)

    def test_gate_fails_closed_on_malformed_pr_metadata(self) -> None:
        """Missing exact-head evidence cannot select a write target."""
        malformed = pull_request(4)
        malformed["head"] = {"sha": "short"}
        self.assertEqual(
            evaluate_gate(
                [malformed],
                [],
                nvidia_key_configured=True,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(
                False,
                "blocked",
                "pull_request_metadata_invalid",
                open_pull_request_count=1,
            ),
        )

    def test_gate_rejects_untrusted_ref_syntax(self) -> None:
        """Head and base refs cannot inject outputs or trusted prompt content."""
        for pull in (
            pull_request(4, head_ref="agent/good\neligible=true"),
            pull_request(4, base_ref="main\rmode=develop_product_gap"),
        ):
            with self.subTest(pull=pull):
                self.assertEqual(
                    evaluate_gate(
                        [pull],
                        [],
                        nvidia_key_configured=True,
                        repository_full_name=_REPOSITORY,
                    ),
                    GateDecision(
                        False,
                        "blocked",
                        "pull_request_metadata_invalid",
                        open_pull_request_count=1,
                    ),
                )

    def test_gate_rejects_pull_request_targeting_another_repository(self) -> None:
        """A foreign base repository cannot become a local write target."""
        self.assertEqual(
            evaluate_gate(
                [pull_request(4, base_repository="outside/other")],
                [],
                nvidia_key_configured=True,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(
                False,
                "blocked",
                "pull_request_metadata_invalid",
                open_pull_request_count=1,
            ),
        )

    def test_pr_maintenance_is_not_blocked_by_stale_product_task_duplicates(
        self,
    ) -> None:
        """Queue-hygiene issues do not halt the selected PR repair run."""
        issues = [
            {"number": 7, "labels": [{"name": "agent-task"}]},
            {"number": 8, "labels": [{"name": "agent-task"}]},
        ]
        decision = evaluate_gate(
            [pull_request(4)],
            issues,
            nvidia_key_configured=True,
            repository_full_name=_REPOSITORY,
        )
        self.assertEqual(decision.mode, "maintain_pull_request")
        self.assertEqual(decision.pull_request_number, 4)

    def test_gate_resumes_one_active_non_pr_issue_when_pr_queue_is_empty(self) -> None:
        """One durable product task is resumed instead of duplicated."""
        issues = [{"number": 7, "labels": [{"name": "agent-task"}]}]
        self.assertEqual(
            evaluate_gate(
                [],
                issues,
                nvidia_key_configured=True,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(
                True,
                "develop_product_gap",
                "resume_agent_task",
                task_number=7,
            ),
        )

    def test_gate_rejects_malformed_durable_task_number_when_queue_is_empty(
        self,
    ) -> None:
        """An agent task without a positive integer number fails closed."""
        issues = [{"number": "7", "labels": [{"name": "agent-task"}]}]
        self.assertEqual(
            evaluate_gate(
                [],
                issues,
                nvidia_key_configured=True,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(False, "blocked", "agent_task_metadata_invalid"),
        )

    def test_gate_stops_for_multiple_active_agent_tasks_when_queue_is_empty(
        self,
    ) -> None:
        """Ambiguous durable product work fails closed when there is no PR."""
        issues = [
            {"number": 7, "labels": [{"name": "agent-task"}]},
            {"number": 8, "labels": [{"name": "agent-task"}]},
        ]
        self.assertEqual(
            evaluate_gate(
                [],
                issues,
                nvidia_key_configured=True,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(False, "blocked", "multiple_active_agent_tasks"),
        )

    def test_gate_ignores_malformed_and_unrelated_labels(self) -> None:
        """Malformed or unrelated labels cannot manufacture active product work."""
        issues = [
            {"number": 7, "labels": "agent-task"},
            {"number": 8, "labels": ["agent-task", {"name": "documentation"}]},
        ]
        self.assertEqual(
            evaluate_gate(
                [],
                issues,
                nvidia_key_configured=True,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(True, "develop_product_gap", "create_agent_task"),
        )

    def test_gate_ignores_pr_shaped_issue_records(self) -> None:
        """The issues endpoint's PR records are not durable product tasks."""
        issues = [{"number": 7, "pull_request": {"url": "https://example.invalid"}}]
        self.assertEqual(
            evaluate_gate(
                [],
                issues,
                nvidia_key_configured=True,
                repository_full_name=_REPOSITORY,
            ),
            GateDecision(True, "develop_product_gap", "create_agent_task"),
        )

    def test_output_value_rejects_multiline_injection(self) -> None:
        """No scalar can add a second GitHub output assignment."""
        for value in ("safe\neligible=true", "safe\rmode=blocked"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _output_value(value)

    def test_main_appends_product_development_outputs(self) -> None:
        """The gate preserves earlier step outputs while adding its fields."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pulls = root / "pulls.json"
            issues = root / "issues.json"
            output = root / "github-output.txt"
            pulls.write_text("[]", encoding="utf-8")
            issues.write_text("[]", encoding="utf-8")
            output.write_text("existing=value\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "NVIDIA_NIM_API_KEY_CONFIGURED": "true",
                    "GITHUB_REPOSITORY": _REPOSITORY,
                },
                clear=False,
            ):
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
                "existing=value\n"
                "eligible=true\n"
                "mode=develop_product_gap\n"
                "reason=create_agent_task\n"
                "task_number=\n"
                "pull_request_number=\n"
                "pull_request_head_sha=\n"
                "pull_request_head_ref=\n"
                "pull_request_base_ref=\n"
                "pull_request_writable=false\n"
                "open_pull_request_count=0\n",
            )

    def test_main_writes_selected_pr_exact_head_outputs(self) -> None:
        """The workflow receives a validated PR lease rather than raw JSON."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pulls = root / "pulls.json"
            issues = root / "issues.json"
            output = root / "github-output.txt"
            pulls.write_text(
                json.dumps([pull_request(2, sha="c" * 40)]),
                encoding="utf-8",
            )
            issues.write_text("[]", encoding="utf-8")
            output.touch()
            with patch.dict(
                os.environ,
                {
                    "NVIDIA_NIM_API_KEY_CONFIGURED": "true",
                    "GITHUB_REPOSITORY": _REPOSITORY,
                },
                clear=False,
            ):
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
            rendered = output.read_text(encoding="utf-8")
            self.assertEqual(return_code, 0)
            self.assertIn("mode=maintain_pull_request\n", rendered)
            self.assertIn("pull_request_number=2\n", rendered)
            self.assertIn(f"pull_request_head_sha={'c' * 40}\n", rendered)
            self.assertIn("pull_request_writable=true\n", rendered)


if __name__ == "__main__":
    unittest.main()
