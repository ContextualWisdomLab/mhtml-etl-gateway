"""Regression contracts for fork pull-request read-only enforcement."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "hourly-product-gap.yml"


def _job_section(workflow_text: str, job_name: str) -> str:
    """Return one top-level job without including a following sibling job."""
    marker = f"  {job_name}:\n"
    start = workflow_text.index(marker)
    match = re.search(r"(?m)^  [a-z0-9_-]+:\n", workflow_text[start + len(marker) :])
    if match is None:
        return workflow_text[start:]
    return workflow_text[start : start + len(marker) + match.start()]


def _step_section(job_text: str, step_name: str) -> str:
    """Return one named step from a bounded job section."""
    marker = f"      - name: {step_name}"
    start = job_text.index(marker)
    next_step = job_text.find("\n      - name: ", start + len(marker))
    return job_text[start:] if next_step < 0 else job_text[start:next_step]


class ForkReadOnlySchedulerContractTests(unittest.TestCase):
    """Ensure a fork decision cannot reach repository-write agent authority."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load and split the scheduler into selection, fork, and writer jobs."""
        cls.workflow = _WORKFLOW.read_text(encoding="utf-8")
        cls.select_job = _job_section(cls.workflow, "select-loop")
        cls.fork_job = _job_section(cls.workflow, "fork-read-only")
        cls.writer_job = _job_section(cls.workflow, "write-loop")
        cls.writer_maintenance = _step_section(
            cls.writer_job,
            "Run OpenCode PR maintenance",
        )
        cls.fork_agent = _step_section(
            cls.fork_job,
            "Run read-only fork triage",
        )

    def test_write_capable_maintenance_requires_same_repository_branch(self) -> None:
        """The privileged GitHub-mode agent runs only for a writable PR head."""
        condition = " ".join(self.writer_maintenance.split())
        self.assertIn(
            "needs.select-loop.outputs.pull_request_writable == 'true'",
            condition,
        )
        self.assertIn("run: opencode github run", self.writer_maintenance)
        self.assertNotIn("pull_request_writable == 'false'", condition)

    def test_fork_path_is_a_separate_read_only_job(self) -> None:
        """Fork triage uses read-only job permissions and no OIDC token authority."""
        flattened = " ".join(self.fork_job.split())
        self.assertIn(
            "needs.select-loop.outputs.pull_request_writable == 'false'",
            flattened,
        )
        for permission in (
            "actions: read",
            "checks: read",
            "contents: read",
            "issues: read",
            "pull-requests: read",
            "security-events: read",
            "statuses: read",
        ):
            self.assertIn(permission, self.fork_job)
        self.assertNotIn("id-token:", self.fork_job)
        self.assertNotRegex(
            self.fork_job,
            r"(?m)^      (?:actions|contents|issues|pull-requests|security-events): write$",
        )

    def test_fork_agent_has_no_github_write_credential_or_github_mode(self) -> None:
        """The model receives evidence and NVIDIA access but no GitHub authority."""
        self.assertIn('run: opencode run --auto "$PROMPT"', self.fork_agent)
        self.assertIn("NVIDIA_API_KEY: ${{ secrets.NVIDIA_NIM_API_KEY }}", self.fork_agent)
        self.assertNotIn("opencode github run", self.fork_agent)
        self.assertNotIn("USE_GITHUB_TOKEN", self.fork_agent)
        self.assertNotIn("GH_TOKEN", self.fork_agent)
        self.assertNotIn("GITHUB_TOKEN", self.fork_agent)
        self.assertNotIn("ACTIONS_ID_TOKEN_REQUEST", self.fork_agent)

    def test_fork_evidence_collection_uses_only_the_read_scoped_job_token(self) -> None:
        """GitHub access occurs before the model step and is confined to evidence files."""
        collection = _step_section(self.fork_job, "Collect read-only fork evidence")
        self.assertIn("GH_TOKEN: ${{ github.token }}", collection)
        self.assertIn(
            'gh api "repos/${GITHUB_REPOSITORY}/pulls/${TARGET_PR_NUMBER}"',
            collection,
        )
        self.assertIn("gh pr diff", collection)
        self.assertIn(".agent/fork-evidence", collection)
        self.assertLess(
            self.fork_job.index("- name: Collect read-only fork evidence"),
            self.fork_job.index("- name: Run read-only fork triage"),
        )

    def test_selection_job_itself_has_no_repository_write_authority(self) -> None:
        """Untrusted queue metadata is classified before any write-capable job starts."""
        self.assertIn("contents: read", self.select_job)
        self.assertIn("issues: read", self.select_job)
        self.assertIn("pull-requests: read", self.select_job)
        self.assertNotIn("id-token:", self.select_job)
        self.assertNotRegex(self.select_job, r"(?m)^      [a-z-]+: write$")


if __name__ == "__main__":
    unittest.main()
