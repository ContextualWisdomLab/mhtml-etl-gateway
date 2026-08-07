"""Supply-chain and exact-source contracts for repository-owned CI."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
QUALITY_LOCK = ROOT / "requirements-quality.txt"
COVERAGE_VERSION = "7.13.3"
COVERAGE_HASHES = {
    "0c2be202a83dde768937a61cdc5d06bf9fb204048ca199d93479488e6247656c",
    "8bb09e83c603f152d855f666d70a71765ca8e67332e5829e62cb9466c176af23",
    "16d23d6579cf80a474ad160ca14d8b319abaa6db62759d6eef53b2fc979b58c8",
    "06e49c5897cb12e3f7ecdc111d44e97c4f6d0557b81a7a0204ed70a8b038f86f",
    "90a8af9dba6429b2573199622d72e0ebf024d6276f16abce394ad4d181bb0910",
}


def _workflow_source() -> str:
    """Return the complete repository-quality workflow as inert text."""
    return CI_WORKFLOW.read_text(encoding="utf-8")


def test_quality_dependency_is_hash_locked_and_installed_fail_closed() -> None:
    """Require the CI-only coverage tool to use an exact hash-checked lock."""
    assert QUALITY_LOCK.is_file(), "requirements-quality.txt must be committed"
    lock = QUALITY_LOCK.read_text(encoding="utf-8")
    workflow = _workflow_source()

    assert f"coverage=={COVERAGE_VERSION}" in lock
    for digest in COVERAGE_HASHES:
        assert f"--hash=sha256:{digest}" in lock

    install_command = (
        "python -m pip install --disable-pip-version-check --no-cache-dir "
        "--only-binary=:all: --require-hashes -r requirements-quality.txt"
    )
    assert install_command in workflow
    assert "pip install --disable-pip-version-check coverage==" not in workflow


def test_pull_request_quality_checks_bind_to_the_exact_source_head() -> None:
    """Reject GitHub's synthetic merge ref as repository test evidence."""
    workflow = _workflow_source()
    checkout = re.search(
        r"(?ms)^      - name: Checkout\n"
        r"        uses: actions/checkout@[0-9a-f]{40}.*?\n"
        r"        with:\n"
        r"(?P<inputs>(?:          .+\n)+?)"
        r"      - name: ",
        workflow,
    )
    assert checkout is not None, "the named Checkout step must remain structurally bounded"
    checkout_inputs = checkout.group("inputs")
    assert "persist-credentials: false" in checkout_inputs
    assert (
        "ref: ${{ github.event_name == 'pull_request' && "
        "github.event.pull_request.head.sha || github.sha }}"
        in checkout_inputs
    )

    verification = (
        "- name: Verify exact pull-request head\n"
        "        if: github.event_name == 'pull_request'\n"
        "        env:\n"
        "          EXPECTED_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n"
        "        run: test \"$(git rev-parse HEAD)\" = \"$EXPECTED_HEAD_SHA\""
    )
    assert verification in workflow
