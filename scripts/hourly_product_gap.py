"""Fail-closed mode selector for hourly PR maintenance and product development."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any

_HEAD_SHA = re.compile(r"^[0-9a-f]{40}$")
_GIT_REF = re.compile(r"^[A-Za-z0-9._/-]{1,255}$")


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Validated execution mode and exact target metadata for the hourly loop."""

    eligible: bool
    mode: str
    reason: str
    task_number: int | None = None
    pull_request_number: int | None = None
    pull_request_head_sha: str | None = None
    pull_request_head_ref: str | None = None
    pull_request_base_ref: str | None = None
    pull_request_writable: bool = False
    open_pull_request_count: int = 0

    def to_dict(self) -> dict[str, str | bool | int | None]:
        """Return a JSON-ready representation of the mode decision."""
        return {
            "eligible": self.eligible,
            "mode": self.mode,
            "reason": self.reason,
            "task_number": self.task_number,
            "pull_request_number": self.pull_request_number,
            "pull_request_head_sha": self.pull_request_head_sha,
            "pull_request_head_ref": self.pull_request_head_ref,
            "pull_request_base_ref": self.pull_request_base_ref,
            "pull_request_writable": self.pull_request_writable,
            "open_pull_request_count": self.open_pull_request_count,
        }


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Load and flatten GitHub API records, including ``gh --slurp`` pages."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("GitHub evidence must be a JSON array")
    records: list[dict[str, Any]] = []
    for item in payload:
        candidates = item if isinstance(item, list) else [item]
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


def _positive_integer(value: object) -> int | None:
    """Return a positive non-boolean integer, or ``None`` for malformed input."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _nested_text(record: dict[str, Any], *path: str) -> str | None:
    """Return a non-empty string at a validated nested-object path."""
    current: object = record
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    if not isinstance(current, str) or not current.strip():
        return None
    return current.strip()


def _pull_request_decision(
    pull_requests: list[dict[str, Any]],
    *,
    repository_full_name: str,
) -> GateDecision:
    """Validate the complete queue and select its lowest-numbered open PR."""
    validated: list[tuple[int, str, str, str, str]] = []
    for pull_request in pull_requests:
        number = _positive_integer(pull_request.get("number"))
        state = pull_request.get("state")
        head_sha = _nested_text(pull_request, "head", "sha")
        head_ref = _nested_text(pull_request, "head", "ref")
        head_repository = _nested_text(pull_request, "head", "repo", "full_name")
        base_ref = _nested_text(pull_request, "base", "ref")
        base_repository = _nested_text(pull_request, "base", "repo", "full_name")
        if (
            number is None
            or state != "open"
            or head_sha is None
            or _HEAD_SHA.fullmatch(head_sha) is None
            or head_ref is None
            or _GIT_REF.fullmatch(head_ref) is None
            or head_repository is None
            or base_ref is None
            or _GIT_REF.fullmatch(base_ref) is None
            or base_repository != repository_full_name
        ):
            return GateDecision(
                False,
                "blocked",
                "pull_request_metadata_invalid",
                open_pull_request_count=len(pull_requests),
            )
        validated.append((number, head_sha, head_ref, base_ref, head_repository))

    number, head_sha, head_ref, base_ref, head_repository = min(
        validated,
        key=lambda item: item[0],
    )
    return GateDecision(
        True,
        "maintain_pull_request",
        "open_pull_request_selected",
        pull_request_number=number,
        pull_request_head_sha=head_sha,
        pull_request_head_ref=head_ref,
        pull_request_base_ref=base_ref,
        pull_request_writable=head_repository == repository_full_name,
        open_pull_request_count=len(pull_requests),
    )


def evaluate_gate(
    pull_requests: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    *,
    repository_full_name: str,
    nvidia_key_configured: bool | None = None,
) -> GateDecision:
    """Choose exact-head PR maintenance first, otherwise bounded product work.

    ``nvidia_key_configured`` is retained only for direct callers that still
    exercise the pre-gateway contract. The workflow entry point deliberately
    omits that provider-specific signal: contextual-orchestrator owns provider
    discovery and its sidecar preflight is the fail-closed capability boundary.
    """
    if nvidia_key_configured is False:
        return GateDecision(False, "blocked", "nvidia_nim_api_key_unconfigured")
    if not repository_full_name.strip():
        return GateDecision(False, "blocked", "repository_metadata_unconfigured")
    if pull_requests:
        return _pull_request_decision(
            pull_requests,
            repository_full_name=repository_full_name,
        )

    active_tasks = [issue for issue in issues if _is_active_agent_issue(issue)]
    if len(active_tasks) > 1:
        return GateDecision(False, "blocked", "multiple_active_agent_tasks")
    if active_tasks:
        task_number = _positive_integer(active_tasks[0].get("number"))
        if task_number is None:
            return GateDecision(False, "blocked", "agent_task_metadata_invalid")
        return GateDecision(
            True,
            "develop_product_gap",
            "resume_agent_task",
            task_number=task_number,
        )
    return GateDecision(True, "develop_product_gap", "create_agent_task")


def _argument_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for workflow evidence paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pull-requests-json", required=True)
    parser.add_argument("--issues-json", required=True)
    parser.add_argument("--github-output", required=True)
    return parser


def _output_value(value: object | None = None) -> str:
    """Render one newline-safe GitHub output scalar."""
    if value is None:
        return ""
    if isinstance(value, bool):
        rendered = str(value).lower()
    else:
        rendered = str(value)
    if "\n" in rendered or "\r" in rendered:
        raise ValueError("GitHub output values must be single-line scalars")
    return rendered


def main(arguments: Sequence[str] | None = None) -> int:
    """Evaluate live evidence and append validated GitHub step outputs."""
    namespace = _argument_parser().parse_args(arguments)
    decision = evaluate_gate(
        load_records(namespace.pull_requests_json),
        load_records(namespace.issues_json),
        repository_full_name=os.environ.get("GITHUB_REPOSITORY", ""),
    )
    fields = (
        "eligible",
        "mode",
        "reason",
        "task_number",
        "pull_request_number",
        "pull_request_head_sha",
        "pull_request_head_ref",
        "pull_request_base_ref",
        "pull_request_writable",
        "open_pull_request_count",
    )
    output_path = Path(namespace.github_output)
    with output_path.open("a", encoding="utf-8") as output_file:
        output_file.write(
            "".join(
                f"{field}={_output_value(getattr(decision, field))}\n"
                for field in fields
            )
        )
    print(json.dumps(decision.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
