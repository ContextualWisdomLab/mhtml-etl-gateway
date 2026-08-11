"""Regression contract for non-terminating autonomous scheduler behavior."""

from __future__ import annotations

from pathlib import Path
import unittest


_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "hourly-product-gap.yml"


def _normalized_step(step_name: str) -> str:
    """Return one workflow step with whitespace normalized for stable assertions."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    marker = f"      - name: {step_name}"
    start = workflow.index(marker)
    end = workflow.find("\n      - name: ", start + len(marker))
    section = workflow[start:] if end < 0 else workflow[start:end]
    return " ".join(section.split())


class SchedulerContinuationContractTests(unittest.TestCase):
    """Prevent status-only or single-action termination from returning."""

    def test_pr_maintenance_defines_material_progress_and_strict_stop_conditions(self) -> None:
        """PR maintenance must keep taking safe work after each intermediate event."""
        prompt = _normalized_step("Run OpenCode PR maintenance")
        required_phrases = (
            "SUCCESS = MATERIAL REPOSITORY PROGRESS",
            "The hourly recurrence is continuation, not deferral",
            "Updating this scheduler or its prompt is an intermediate event, never an end condition",
            "Do not save feasible work for the next hourly run",
            "Stop only when the finite execution budget is genuinely exhausted",
            "a fresh full-queue scan proves every remaining item is non-actionable under current authority",
            "After the open PR queue reaches zero or only external blockers remain, immediately continue with issues, documentation completeness, release readiness, buyer-visible gaps, and ecosystem integration",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, prompt)

    def test_product_development_continues_after_prompt_issue_commit_and_pr_events(self) -> None:
        """Product development treats every artifact mutation as an intermediate event."""
        prompt = _normalized_step("Run OpenCode product development")
        required_phrases = (
            "SUCCESS = MATERIAL REPOSITORY PROGRESS",
            "The hourly recurrence is continuation, not deferral",
            "A prompt update, issue update, commit, or newly created PR is an intermediate event, never an end condition",
            "Do not save feasible work for the next hourly run",
            "Stop only when the finite execution budget is genuinely exhausted",
            "a fresh full-queue scan proves every remaining item is non-actionable under current authority",
            "After publishing a PR, immediately continue with exact-head repair, documentation, release preparation, ecosystem integration, or the next demonstrably disjoint buyer-visible slice",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, prompt)


if __name__ == "__main__":
    unittest.main()
