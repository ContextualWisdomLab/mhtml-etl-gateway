"""Regression tests for provider-independent hourly-loop admission."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from scripts.hourly_product_gap import main

_REPOSITORY = "ContextualWisdomLab/mhtml-etl-gateway"


def test_main_does_not_require_legacy_nvidia_marker() -> None:
    """The selector must reach the CO sidecar when a non-NVIDIA provider may serve it."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        pulls = root / "pulls.json"
        issues = root / "issues.json"
        output = root / "github-output.txt"
        pulls.write_text("[]", encoding="utf-8")
        issues.write_text("[]", encoding="utf-8")
        output.touch()

        with patch.dict(
            os.environ,
            {
                "NVIDIA_NIM_API_KEY_CONFIGURED": "false",
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
        assert return_code == 0
        assert "eligible=true\n" in rendered
        assert "mode=develop_product_gap\n" in rendered
        assert "reason=create_agent_task\n" in rendered
