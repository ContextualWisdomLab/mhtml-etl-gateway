"""Supply-chain contracts for repository-owned quality dependencies."""

from __future__ import annotations

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


def test_quality_dependency_is_hash_locked_and_installed_fail_closed() -> None:
    """Require the CI-only coverage tool to use an exact hash-checked lock."""
    assert QUALITY_LOCK.is_file(), "requirements-quality.txt must be committed"
    lock = QUALITY_LOCK.read_text(encoding="utf-8")
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert f"coverage=={COVERAGE_VERSION}" in lock
    for digest in COVERAGE_HASHES:
        assert f"--hash=sha256:{digest}" in lock

    install_command = (
        "python -m pip install --disable-pip-version-check --no-cache-dir "
        "--only-binary=:all: --require-hashes -r requirements-quality.txt"
    )
    assert install_command in workflow
    assert "pip install --disable-pip-version-check coverage==" not in workflow
