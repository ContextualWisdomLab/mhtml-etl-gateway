"""Tests for immutable and least-privilege GitHub workflow contracts."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


class WorkflowContractTests(unittest.TestCase):
    """Prevent workflow drift that weakens supply-chain or scheduler controls."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load workflow and OpenCode configuration text once."""
        cls.ci_text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        cls.hourly_text = Path(".github/workflows/hourly-product-gap.yml").read_text(encoding="utf-8")
        cls.opencode_text = Path("opencode.jsonc").read_text(encoding="utf-8")

    def test_every_action_reference_is_an_immutable_sha(self) -> None:
        """Mutable action tags cannot enter either workflow."""
        references = re.findall(r"^\s*uses:\s*([^\s#]+)", self.ci_text + "\n" + self.hourly_text, re.MULTILINE)
        self.assertGreaterEqual(len(references), 4)
        for reference in references:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")

    def test_hourly_loop_uses_nvidia_nim_and_never_copilot(self) -> None:
        """The development scheduler binds only the approved NIM secret contract."""
        combined = self.hourly_text + self.opencode_text
        self.assertIn("NVIDIA_NIM_API_KEY", combined)
        self.assertIn("NVIDIA_API_KEY", combined)
        self.assertIn("nvidia-nim/", combined)
        self.assertNotIn("COPILOT_GITHUB_TOKEN", combined)

    def test_hourly_loop_never_shares_public_agent_sessions(self) -> None:
        """Public repositories must keep scheduled OpenCode sessions private."""
        self.assertIn("share: false", self.hourly_text)

    def test_hourly_loop_is_default_branch_schedule_only(self) -> None:
        """No branch-selectable privileged manual trigger is shipped."""
        self.assertIn('cron: "23 * * * *"', self.hourly_text)
        self.assertNotIn("workflow_dispatch", self.hourly_text)
        self.assertNotIn("pull_request", self.hourly_text.split("jobs:", 1)[0])

    def test_hourly_loop_has_single_flight_and_preflight_gate(self) -> None:
        """Overlapping agent runs and duplicate PR work are structurally blocked."""
        self.assertIn("cancel-in-progress: false", self.hourly_text)
        self.assertIn("scripts/hourly_product_gap.py", self.hourly_text)
        self.assertIn("steps.product_gate.outputs.eligible == 'true'", self.hourly_text)

    def test_hourly_loop_uses_durable_agent_task_lease(self) -> None:
        """A failed agent run is resumable without creating duplicate branches or PRs."""
        self.assertIn("Ensure one durable agent task", self.hourly_text)
        self.assertIn("agent-task", self.hourly_text)
        self.assertIn("steps.ensure_task.outputs.task_number", self.hourly_text)
        self.assertIn("id-token: write", self.hourly_text)
        self.assertIn("Close the", self.hourly_text)
        self.assertIn("agent-task issue only after", self.hourly_text)

    def test_repository_does_not_duplicate_central_merge_scheduler(self) -> None:
        """Local automation owns product work, not PR review or merge governance."""
        self.assertNotIn("merge_pull_request", self.hourly_text)
        self.assertNotIn("enable_auto_merge", self.hourly_text)
        self.assertNotIn("pr-review-merge-scheduler", self.hourly_text)

    def test_ci_requires_exact_line_and_branch_coverage(self) -> None:
        """The local quality lane rejects anything below 100 percent."""
        self.assertIn("coverage run --branch", self.ci_text)
        self.assertIn("coverage report --show-missing --fail-under=100", self.ci_text)
        self.assertIn('python-version: ["3.11", "3.12", "3.13", "3.14"]', self.ci_text)


if __name__ == "__main__":
    unittest.main()
