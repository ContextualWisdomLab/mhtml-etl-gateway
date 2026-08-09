"""Supply-chain contracts for the privileged OpenCode scheduler executable."""

from __future__ import annotations

from pathlib import Path
import unittest


_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "hourly-product-gap.yml"
_VERSION = "1.18.15"
_LINUX_X64_SHA256 = "d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c"


def _step_section(workflow_text: str, step_name: str) -> str:
    """Return one named workflow step as a stable text region."""
    marker = f"      - name: {step_name}"
    start = workflow_text.index(marker)
    next_step = workflow_text.find("\n      - name: ", start + len(marker))
    return workflow_text[start:] if next_step < 0 else workflow_text[start:next_step]


class OpenCodeRunnerSupplyChainTests(unittest.TestCase):
    """Require an exact, hash-verified CLI before privileged agent execution."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the hourly workflow once for structural assertions."""
        cls.workflow = _WORKFLOW.read_text(encoding="utf-8")
        cls.install_step = _step_section(cls.workflow, "Install verified OpenCode CLI")
        cls.maintenance_step = _step_section(cls.workflow, "Run OpenCode PR maintenance")
        cls.product_step = _step_section(cls.workflow, "Run OpenCode product development")

    def test_dynamic_composite_installer_is_not_used(self) -> None:
        """Mutable nested actions, latest lookup, and remote script piping stay absent."""
        prohibited = (
            "anomalyco/opencode/github@",
            "actions/cache@",
            "releases/latest",
            "https://opencode.ai/install",
            "curl -fsSL https://opencode.ai/install | bash",
        )
        for fragment in prohibited:
            self.assertNotIn(fragment, self.workflow)

    def test_exact_linux_archive_is_verified_before_installation(self) -> None:
        """The scheduled runner accepts only the reviewed v1.18.15 Linux x64 bytes."""
        self.assertIn(f'OPENCODE_VERSION: "{_VERSION}"', self.install_step)
        self.assertIn(f'OPENCODE_SHA256: "{_LINUX_X64_SHA256}"', self.install_step)
        self.assertIn(
            "https://github.com/anomalyco/opencode/releases/download/"
            "v${OPENCODE_VERSION}/opencode-linux-x64.tar.gz",
            self.install_step,
        )
        self.assertIn("sha256sum --check --strict", self.install_step)
        self.assertIn("tar --extract --gzip", self.install_step)
        self.assertIn("--no-same-owner", self.install_step)
        self.assertIn("--no-same-permissions", self.install_step)
        self.assertIn('test "$actual_version" = "$OPENCODE_VERSION"', self.install_step)
        self.assertLess(
            self.workflow.index("- name: Install verified OpenCode CLI"),
            self.workflow.index("- name: Run OpenCode PR maintenance"),
        )

    def test_installation_step_receives_no_model_or_repository_credentials(self) -> None:
        """Digest and version failures occur before privileged credentials are exposed."""
        prohibited = (
            "NVIDIA_API_KEY",
            "NVIDIA_NIM_API_KEY",
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
            "ACTIONS_ID_TOKEN_REQUEST_URL",
        )
        for fragment in prohibited:
            self.assertNotIn(fragment, self.install_step)

    def test_verified_binary_runs_both_agent_modes_directly(self) -> None:
        """Both modes use the verified binary without another installation boundary."""
        for step in (self.maintenance_step, self.product_step):
            self.assertIn("run: opencode github run", step)
            self.assertIn("NVIDIA_API_KEY: ${{ secrets.NVIDIA_NIM_API_KEY }}", step)
            self.assertIn("MODEL: nvidia-nim/nvidia/llama-3.3-nemotron-super-49b-v1.5", step)
            self.assertIn('SHARE: "false"', step)
            self.assertIn("PROMPT: |", step)
            self.assertNotIn("uses: anomalyco/opencode", step)


if __name__ == "__main__":
    unittest.main()
