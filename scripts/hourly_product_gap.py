"""Fail-closed single-flight gate for the hourly OpenCode product loop."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
from collections.abc import Sequence
from typing import Any


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Eligibility result emitted to both logs and GitHub step outputs."""

    eligible: bool
    reason: str
    task_number: int | None = None

    def to_dict(self) -> dict[str, str | bool | int | None]:
        """Return a JSON-ready representation of the decision."""
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "task_number": self.task_number,
        }


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Load and flatten GitHub API records, including ``gh --slurp`` pages."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("GitHub evidence must be a JSON array")
    records: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, list):
            candidates = item
        else:
            candidates = [item]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("Every GitHub evidence record must be an object")
            records.append(candidate)
    return records


def _is_active_agent_issue(issue: dict[str, Any]) -> bool:
    """Return whether an issue is a non-PR task carrying the agent-task label."""
    if "pull_request" in issue:
        return False
    labels = issue.get("labels", [])
    if not isinstance(labels, list):
        return False
    return any(
        isinstance(label, dict) and label.get("name") == "agent-task"
        for label in labels
    )


def evaluate_gate(
    pull_requests: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    *,
    nvidia_key_configured: bool,
) -> GateDecision:
    """Apply credential and single-flight rules to current repository evidence."""
    if not nvidia_key_configured:
        return GateDecision(False, "nvidia_nim_api_key_unconfigured")
    if pull_requests:
        return GateDecision(False, "open_pull_request_exists")
    active_tasks = [issue for issue in issues if _is_active_agent_issue(issue)]
    if len(active_tasks) > 1:
        return GateDecision(False, "multiple_active_agent_tasks")
    if active_tasks:
        task_number = active_tasks[0].get("number")
        if isinstance(task_number, bool) or not isinstance(task_number, int) or task_number <= 0:
            return GateDecision(False, "agent_task_metadata_invalid")
        return GateDecision(True, "resume_agent_task", task_number=task_number)
    return GateDecision(True, "create_agent_task")


def _argument_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for workflow evidence paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pull-requests-json", required=True)
    parser.add_argument("--issues-json", required=True)
    parser.add_argument("--github-output", required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Evaluate eligibility, write GitHub outputs, and print audit evidence."""
    namespace = _argument_parser().parse_args(arguments)
    decision = evaluate_gate(
        load_records(namespace.pull_requests_json),
        load_records(namespace.issues_json),
        nvidia_key_configured=bool(os.environ.get("NVIDIA_NIM_API_KEY", "")),
    )
    output_path = Path(namespace.github_output)
    task_number = "" if decision.task_number is None else str(decision.task_number)
    output_path.write_text(
        (
            f"eligible={str(decision.eligible).lower()}\n"
            f"reason={decision.reason}\n"
            f"task_number={task_number}\n"
        ),
        encoding="utf-8",
    )
    print(json.dumps(decision.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
