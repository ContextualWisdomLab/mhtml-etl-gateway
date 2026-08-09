"""Deterministic repository quality validation used locally and in CI."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Sequence
import json
from pathlib import Path
import re

REQUIRED_DOCUMENTS = (
    Path("README.md"),
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path("CHANGELOG.md"),
    Path("SECURITY.md"),
    Path("docs/PRD.md"),
    Path("docs/TRD.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("docs/UML.md"),
    Path("docs/DATA_MODEL.md"),
    Path("docs/ERD.md"),
    Path("docs/API_CONTRACT.md"),
    Path("docs/SECURITY.md"),
    Path("docs/THREAT_MODEL.md"),
    Path("docs/TEST_STRATEGY.md"),
    Path("docs/OPERABILITY.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/COMPLIANCE_CONTROL_MAP.md"),
    Path("docs/RESEARCH_TRACEABILITY.md"),
    Path("docs/VALIDATION_REPORT.md"),
    Path("docs/adr/README.md"),
    Path("docs/doctoring/REFERENCES.md"),
)

_WORKFLOW_ROOT = Path(".github/workflows")
_HOURLY_WORKFLOW = _WORKFLOW_ROOT / "hourly-product-gap.yml"
_ACTION_REFERENCE = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
_IMMUTABLE_ACTION_REFERENCE = re.compile(r"^[^@]+@[0-9a-f]{40}$")
_PLACEHOLDER = re.compile(r"\b(?:TODO|TBD|PLACEHOLDER|FIXME)\b", re.IGNORECASE)


def _public_nodes(tree: ast.AST) -> Iterable[tuple[str, ast.AST]]:
    """Yield public top-level symbols and public members from a Python syntax tree."""
    for node in getattr(tree, "body", []):
        if isinstance(
            node,
            (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ) and not node.name.startswith("_"):
            yield node.name, node
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for member in node.body:
                if isinstance(
                    member,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ) and not member.name.startswith("_"):
                    yield f"{node.name}.{member.name}", member


def missing_public_docstrings(roots: tuple[Path, ...]) -> list[str]:
    """Return public Python modules and symbols that lack explanatory docstrings."""
    missing: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
            if ast.get_docstring(tree) is None:
                missing.append(str(path))
            for qualified_name, node in _public_nodes(tree):
                if ast.get_docstring(node) is None:
                    missing.append(f"{path}:{qualified_name}")
    return missing


def find_mutable_action_references(
    workflow_paths: tuple[Path, ...],
) -> list[tuple[Path, str]]:
    """Return GitHub Action references that are not pinned to full commit SHAs."""
    mutable: list[tuple[Path, str]] = []
    for path in workflow_paths:
        text = path.read_text(encoding="utf-8")
        for reference in _ACTION_REFERENCE.findall(text):
            if not _IMMUTABLE_ACTION_REFERENCE.fullmatch(reference):
                mutable.append((path, reference))
    return mutable


def _workflow_paths() -> tuple[Path, ...]:
    """Return every nested YAML workflow under the repository workflow root."""
    paths = {
        path
        for pattern in ("*.yml", "*.yaml")
        for path in _WORKFLOW_ROOT.rglob(pattern)
        if path.is_file()
    }
    return tuple(sorted(paths))


def _validation_errors() -> list[str]:
    """Collect every deterministic repository contract violation."""
    errors: list[str] = []
    for path in REQUIRED_DOCUMENTS:
        if not path.is_file():
            errors.append(f"missing required document: {path}")
    errors.extend(
        f"missing public docstring: {item}"
        for item in missing_public_docstrings((Path("src"), Path("scripts")))
    )

    workflow_paths = _workflow_paths()
    errors.extend(
        f"mutable action reference in {path}: {reference}"
        for path, reference in find_mutable_action_references(workflow_paths)
    )
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in workflow_paths
    )
    if "COPILOT_GITHUB_TOKEN" in workflow_text:
        errors.append("prohibited scheduler credential appears in a workflow")

    if not _HOURLY_WORKFLOW.is_file():
        errors.append(f"missing required workflow: {_HOURLY_WORKFLOW}")
    else:
        hourly_workflow_text = _HOURLY_WORKFLOW.read_text(encoding="utf-8")
        if "secrets.NVIDIA_NIM_API_KEY" not in hourly_workflow_text:
            errors.append("hourly product workflow does not bind NVIDIA_NIM_API_KEY")
        if "share: false" not in hourly_workflow_text:
            errors.append(
                "hourly product workflow does not disable OpenCode session sharing"
            )

    source_artifacts = sorted(
        path
        for pattern in ("*.mhtml", "*.mht")
        for path in Path(".").rglob(pattern)
        if ".git" not in path.parts
    )
    errors.extend(
        f"customer-like MHTML artifact must not be committed: {path}"
        for path in source_artifacts
    )
    for path in REQUIRED_DOCUMENTS:
        if path.is_file() and _PLACEHOLDER.search(
            path.read_text(encoding="utf-8")
        ):
            errors.append(f"unresolved placeholder token in {path}")
    return errors


def _argument_parser() -> argparse.ArgumentParser:
    """Create the currently option-free validation command parser."""
    return argparse.ArgumentParser(description=__doc__)


def main(arguments: Sequence[str] | None = None) -> int:
    """Validate the repository and emit one machine-readable result object."""
    _argument_parser().parse_args(arguments)
    errors = _validation_errors()
    payload = {"status": "failed" if errors else "passed", "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
