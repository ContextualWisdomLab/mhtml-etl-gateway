"""Regression contracts for the work-conserving autonomous scheduler."""

from __future__ import annotations

from pathlib import Path
import unittest


_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "hourly-product-gap.yml"


def _step_section(workflow_text: str, step_name: str) -> str:
    """Return one named workflow step without relying on a leading split token."""
    marker = f"      - name: {step_name}"
    start = workflow_text.index(marker)
    next_step = workflow_text.find("\n      - name: ", start + len(marker))
    return workflow_text[start:] if next_step < 0 else workflow_text[start:next_step]


class AutonomousContinuationContractTests(unittest.TestCase):
    """Prevent the scheduler from stopping after one blocker or completed action."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load raw and whitespace-normalized workflow text once."""
        cls.workflow_text = _WORKFLOW.read_text(encoding="utf-8")
        cls.workflow_flat = " ".join(cls.workflow_text.split())

    def test_secret_stripping_wrapper_precedes_repository_gate(self) -> None:
        """Repository code cannot run before the credential-free wrapper exists."""
        wrapper_position = self.workflow_text.index(
            "- name: Install secret-stripping execution wrapper"
        )
        gate_position = self.workflow_text.index(
            "- name: Select exact-head loop mode"
        )
        self.assertLess(wrapper_position, gate_position)
        gate_section = _step_section(
            self.workflow_text,
            "Select exact-head loop mode",
        )
        self.assertIn("NVIDIA_NIM_API_KEY_CONFIGURED", gate_section)
        self.assertNotIn("NVIDIA_NIM_API_KEY: ${{", gate_section)
        self.assertIn("cwl-safe-exec python scripts/hourly_product_gap.py", gate_section)

    def test_gate_uses_workspace_evidence_instead_of_privileged_temp_paths(self) -> None:
        """The unprivileged gate reads and writes only group-scoped workspace files."""
        self.assertIn("$GITHUB_WORKSPACE/.agent/evidence/open-pulls.json", self.workflow_text)
        self.assertIn("$GITHUB_WORKSPACE/.agent/evidence/agent-issues.json", self.workflow_text)
        self.assertIn("$GITHUB_WORKSPACE/.agent/evidence/loop-output.txt", self.workflow_text)
        self.assertIn('cat "$gate_output" >> "$GITHUB_OUTPUT"', self.workflow_text)

    def test_gate_output_is_group_writable_before_unprivileged_execution(self) -> None:
        """The isolated gate can append outputs without inheriting runner ownership."""
        gate_section = _step_section(
            self.workflow_text,
            "Select exact-head loop mode",
        )
        self.assertIn('install -m 0660 /dev/null "$gate_output"', gate_section)
        self.assertNotIn(': > "$gate_output"', gate_section)
        self.assertLess(
            gate_section.index('install -m 0660 /dev/null "$gate_output"'),
            gate_section.index("cwl-safe-exec python scripts/hourly_product_gap.py"),
        )

    def test_wrapper_uses_a_dedicated_workspace_group(self) -> None:
        """The untrusted identity never inherits the hosted runner's default group."""
        self.assertIn("groupadd --system cwl-workspace", self.workflow_text)
        self.assertIn("usermod -a -G cwl-workspace cwl-untrusted", self.workflow_text)
        self.assertIn('chown -R "$(id -un):cwl-workspace"', self.workflow_text)
        self.assertNotIn('runner_group="$(id -gn)"', self.workflow_text)
        self.assertNotIn('usermod -a -G "$runner_group"', self.workflow_text)

    def test_maintenance_loop_is_execution_first_and_work_conserving(self) -> None:
        """One blocked action or queued gate cannot terminate the invocation."""
        required_phrases = (
            "EXECUTION-FIRST / ZERO-NARRATION",
            "Routine user-visible output should be empty",
            "A blocked action blocks only that action, never the invocation",
            "Do not terminate after one finding, patch, PR, failed remedy",
            "central merge automation owns the final action, do not wait for merge completion",
            "After every action, refetch live state and immediately select the next executable item",
            "Do not ask the user for routine confirmations or next steps",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, self.workflow_flat)

    def test_blocked_pr_yields_to_other_prs_and_disjoint_product_work(self) -> None:
        """An external approval dependency cannot starve unrelated executable work."""
        required_phrases = (
            "Continue to the next PR or repository-owned task",
            "An unchanged external blocker gets one deduplicated record, not repeated analysis",
            "Open PRs are not a blanket prohibition on disjoint product work",
            "create at most one extra draft PR per invocation",
            "no overlap in files, schemas, migrations, generated artifacts",
            "keep the open PR count minimal",
        )
        lowered = self.workflow_flat.lower()
        for phrase in required_phrases:
            self.assertIn(phrase.lower(), lowered)

    def test_product_mode_switches_to_maintenance_instead_of_stopping(self) -> None:
        """A newly appeared PR suspends only conflicting work and preserves progress."""
        required_phrases = (
            "If a PR appears after the gate, do not terminate",
            "switch to exact-head PR maintenance",
            "then resume this slice or choose a demonstrably disjoint one",
            "a newly created PR is not a reason to end the run",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, self.workflow_flat)


if __name__ == "__main__":
    unittest.main()
