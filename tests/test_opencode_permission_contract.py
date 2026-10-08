"""Security contracts for the scheduled OpenCode command allowlist."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _ROOT / "opencode.jsonc"


class OpenCodePermissionContractTests(unittest.TestCase):
    """Prevent broad raw API or shell authority from re-entering the agent config."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the comment-free repository JSONC configuration once."""
        cls.configuration = json.loads(_CONFIG.read_text(encoding="utf-8"))
        cls.bash_permissions = cls.configuration["permission"]["bash"]

    def test_raw_github_api_requires_an_explicit_get_method(self) -> None:
        """Generic `gh api` access cannot infer POST from supplied fields."""
        allowed_get_patterns = {
            "gh api --method GET *",
            "gh api -X GET *",
            "gh api --paginate --method GET *",
            "gh api --paginate --slurp --method GET *",
        }
        self.assertEqual(
            {
                pattern
                for pattern, decision in self.bash_permissions.items()
                if pattern.startswith("gh api ") and decision == "allow"
            },
            allowed_get_patterns,
        )
        self.assertNotIn("gh api *", self.bash_permissions)

    def test_no_raw_api_mutation_form_is_allowlisted(self) -> None:
        """POST-like flags cannot be approved by any raw GitHub API pattern."""
        forbidden_tokens = (
            "POST",
            "PATCH",
            "PUT",
            "DELETE",
            "--input",
            "--field",
            "--raw-field",
            " -f",
            " -F",
        )
        for pattern, decision in self.bash_permissions.items():
            if not pattern.startswith("gh api ") or decision != "allow":
                continue
            for token in forbidden_tokens:
                self.assertNotIn(token, pattern)

    def test_shell_defaults_to_deny_and_repository_code_uses_wrapper(self) -> None:
        """Only the secret-stripping wrapper may launch repository-controlled code."""
        self.assertEqual(self.bash_permissions["*"], "deny")
        self.assertEqual(
            self.bash_permissions["cwl-safe-exec *"],
            "allow",
        )
        for direct_command in (
            "python *",
            "python3 *",
            "pip *",
            "bash *",
            "sh *",
            "env *",
            "printenv *",
            "curl *",
            "wget *",
        ):
            self.assertNotEqual(
                self.bash_permissions.get(direct_command),
                "allow",
            )


if __name__ == "__main__":
    unittest.main()
