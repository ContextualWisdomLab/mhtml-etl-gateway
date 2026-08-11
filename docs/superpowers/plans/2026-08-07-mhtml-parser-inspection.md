# Deterministic MHTML Parser and Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free, fail-closed MHTML inspection CLI that resolves root HTML, extracts bounded tables, and emits metadata-only lineage evidence.

**Architecture:** A standard-library MIME layer selects and decodes the root HTML; a separate non-rendering HTML parser normalizes bounded tables; an inspection service hashes the immutable source and exposes only structural metadata. Stable error codes isolate expected untrusted-input failures from unexpected defects.

**Tech Stack:** Python 3.11–3.14, standard library `email`, `html.parser`, `argparse`, `hashlib`, `json`, `unittest`, coverage.py 7.13.3, setuptools 82.0.1.

## Global Constraints

- Never execute MHTML active content or fetch external resources.
- Never modify or commit the supplied enterprise source file.
- Every public module, class, function, method, and property requires a useful docstring.
- Production statement and branch coverage must both equal 100%.
- Database and future persistence object names must contain at least two words and use `snake_case` by default.
- Parsing failures fail closed with stable error codes.
- Default CLI output must not contain any cell-derived values, raw Content-Location, or embedded resource payloads.
- All GitHub Actions must be pinned to immutable commit SHAs.
- Central organization required workflows own PR review, security, and merge scheduling; do not copy them locally.

---

### Task 1: Package and error contract

**Files:**
- Create: `pyproject.toml`
- Create: `src/mhtml_etl_gateway/__init__.py`
- Create: `src/mhtml_etl_gateway/errors.py`
- Test: `tests/test_errors.py`

**Interfaces:**
- Produces: `ErrorCode`, `MhtmlGatewayError(code: ErrorCode, message: str)`, package version `__version__`.

- [ ] **Step 1: Write failing tests for stable string error codes, exception rendering, and package version.**
- [ ] **Step 2: Run `python -m unittest tests.test_errors -v` and confirm import failure.**
- [ ] **Step 3: Implement the minimal enum, exception, package export, and packaging metadata.**
- [ ] **Step 4: Run the focused test and confirm success.**
- [ ] **Step 5: Record the change as `feat: define parser error contract`.**

### Task 2: Immutable model and limit contracts

**Files:**
- Create: `src/mhtml_etl_gateway/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `ParseLimits`, `Diagnostic`, `MhtmlDocument`, `TableCell`, `ExtractedTable`, `TableInspection`, `InspectionReport` and each contract's `to_dict()` where applicable.

- [ ] **Step 1: Write failing tests for positive limits, immutable dataclasses, rectangular table validation, and metadata-only serialization, Content-Location hashing, and protected header opt-in.**
- [ ] **Step 2: Run `python -m unittest tests.test_models -v` and confirm missing-symbol failures.**
- [ ] **Step 3: Implement minimal frozen dataclasses and validation.**
- [ ] **Step 4: Run focused tests and confirm success.**
- [ ] **Step 5: Record the change as `feat: add immutable inspection contracts`.**

### Task 3: Bounded MIME parser

**Files:**
- Create: `src/mhtml_etl_gateway/mime_parser.py`
- Create: `tests/fixture_factory.py`
- Test: `tests/test_mime_parser.py`

**Interfaces:**
- Consumes: `ParseLimits`, `Diagnostic`, `MhtmlDocument`, `MhtmlGatewayError`.
- Produces: `parse_mhtml_bytes(source_bytes: bytes, *, limits: ParseLimits | None = None) -> MhtmlDocument`; `parse_mhtml_file(source_path: str | Path, *, limits: ParseLimits | None = None) -> MhtmlDocument`.

- [ ] **Step 1: Write failing tests for multipart root selection, first-body default-root enforcement, standalone HTML, source limits, MIME part limits, missing roots, unknown charset, BOM decoding, and non-file paths.**
- [ ] **Step 2: Run the focused suite and confirm failures are due to missing parser behavior.**
- [ ] **Step 3: Implement bounded MIME parsing and strict root decoding.**
- [ ] **Step 4: Run the focused suite and confirm success.**
- [ ] **Step 5: Record the change as `feat: parse MHTML roots deterministically`.**

### Task 4: Bounded HTML table extraction

**Files:**
- Create: `src/mhtml_etl_gateway/html_tables.py`
- Test: `tests/test_html_tables.py`

**Interfaces:**
- Consumes: decoded `MhtmlDocument`, `ParseLimits`, `MhtmlGatewayError`.
- Produces: `extract_tables(document: MhtmlDocument, *, limits: ParseLimits | None = None) -> tuple[ExtractedTable, ...]`.

- [ ] **Step 1: Write failing tests for header inference, Korean text, whitespace, `<br>`, suppressed active content, data-URI non-leakage, multiple tables, spans, nested-table rejection, malformed spans, and every table resource limit.**
- [ ] **Step 2: Run the focused suite and verify the expected missing-implementation failures.**
- [ ] **Step 3: Implement a non-rendering `HTMLParser` subclass and span normalizer.**
- [ ] **Step 4: Run the focused suite and confirm success.**
- [ ] **Step 5: Record the change as `feat: extract bounded HTML tables`.**

### Task 5: Inspection service and CLI

**Files:**
- Create: `src/mhtml_etl_gateway/inspection.py`
- Create: `src/mhtml_etl_gateway/cli.py`
- Create: `src/mhtml_etl_gateway/__main__.py`
- Test: `tests/test_inspection.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: MIME and table APIs from Tasks 3–4.
- Produces: `inspect_mhtml_bytes`, `inspect_mhtml_file`, `main(arguments: Sequence[str] | None = None) -> int`.

- [ ] **Step 1: Write failing tests for deterministic SHA-256, dimensions, diagnostics, metadata-only serialization, Content-Location hashing, and protected header opt-in, pretty/compact CLI JSON, and fail-closed JSON errors.**
- [ ] **Step 2: Run focused tests and confirm failure.**
- [ ] **Step 3: Implement inspection aggregation and CLI.**
- [ ] **Step 4: Run focused tests and confirm success.**
- [ ] **Step 5: Record the change as `feat: add safe MHTML inspection CLI`.**

### Task 6: Quality, documentation, and real-sample validation

**Files:**
- Create: `tests/test_docstrings.py`
- Create: `tests/test_realistic_export.py`
- Create: `scripts/validate_repository.py`
- Create: `docs/PRD.md`
- Create: `docs/TRD.md`
- Create: `docs/DATA_MODEL.md`
- Create: `docs/SECURITY.md`
- Create: `docs/TEST_STRATEGY.md`
- Create: `docs/OPERABILITY.md`
- Create: `docs/doctoring/REFERENCES.md`
- Create: `docs/adr/0001-non-rendering-parser-boundary.md`
- Create: `docs/adr/0002-immutable-source-identity.md`
- Create: `docs/adr/0003-rfc2387-root-resolution.md`
- Create: `docs/adr/0004-bounded-standard-library-parser.md`
- Create: `docs/adr/0005-metadata-only-default-output.md`
- Create: `docs/adr/0006-central-workflow-inheritance.md`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: repository validator command `python scripts/validate_repository.py`; complete standards traceability and operational contract.

- [ ] **Step 1: Write failing docstring and repository-contract tests.**
- [ ] **Step 2: Run all tests and confirm the intended documentation/contract failures.**
- [ ] **Step 3: Write documentation, ADRs, references, and repository validator.**
- [ ] **Step 4: Run `coverage run --branch -m unittest discover -s tests -t . -v` and `coverage report --show-missing --fail-under=100`.**
- [ ] **Step 5: Run `python -m compileall -q src tests scripts`, `python scripts/validate_repository.py`, and `python -m pip wheel . --no-deps --wheel-dir dist`.**
- [ ] **Step 6: Run a noncommitted protected local smoke test against an operator-held enterprise sample; assert the expected aggregate table, column, and data-row counts without printing or committing its filename, path, hash, headers, or row values.**
- [ ] **Step 7: Record the change as `docs: establish commercial parser baseline`.**

### Task 7: Exact-head CI and autonomous governance contract

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/hourly-product-gap.yml`
- Create: `scripts/hourly_product_gap.py`
- Test: `tests/test_workflow_contracts.py`
- Test: `tests/test_hourly_product_gap.py`
- Create: `docs/adr/0007-hourly-product-development-loop.md`

**Interfaces:**
- Produces: local quality workflow; bounded hourly product-gap issue orchestration that never duplicates the central PR merge scheduler and never uses `COPILOT_GITHUB_TOKEN`.

- [ ] **Step 1: Write failing tests that parse workflow text and reject mutable action tags, duplicate merge schedulers, missing `NVIDIA_NIM_API_KEY`, missing single-flight guards, or `COPILOT_GITHUB_TOKEN`.**
- [ ] **Step 2: Run the focused tests and confirm expected failures.**
- [ ] **Step 3: Implement SHA-pinned CI and a fail-closed hourly product-gap workflow. The workflow creates or resumes one durable `agent-task` issue only when no PR is open; it exposes `NVIDIA_NIM_API_KEY` as `NVIDIA_API_KEY`, sets `share: false`, grants bounded repository write permissions needed for one branch/PR, and never merges or releases.**
- [ ] **Step 4: Run all tests and static workflow validation.**
- [ ] **Step 5: Record the change as `ci: add bounded autonomous development loop`.**

### Task 8: Publish and protected-branch verification

**Files:**
- Create branch: `feat/deterministic-mhtml-inspection`
- Open PR against: `main`

**Interfaces:**
- Consumes: verified local tree.
- Produces: reviewable GitHub PR with exact-head CI evidence.

- [ ] **Step 1: Re-run the full verification suite immediately before publication.**
- [ ] **Step 2: Publish the exact verified tree to the feature branch and open a draft PR linked to the implementation issue.**
- [ ] **Step 3: Inspect all reviews, unresolved threads, security findings, and exact-head workflow runs.**
- [ ] **Step 4: Reproduce each actionable finding with a failing test, patch it, and re-run full verification.**
- [ ] **Step 5: Mark ready only after local quality evidence is current and the PR description matches the exact head.**
- [ ] **Step 6: Merge only when central required workflows, independent approval, unresolved-thread policy, and exact-head checks permit it.**
