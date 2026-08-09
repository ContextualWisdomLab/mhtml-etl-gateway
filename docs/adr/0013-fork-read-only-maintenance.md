# ADR 0013: Enforce fork pull-request triage in a read-only GitHub job

**Status:** Accepted  
**Date:** 2026-08-09

## Context

The hourly gate identifies whether an open pull request's head branch belongs to `ContextualWisdomLab/mhtml-etl-gateway`. Earlier workflow versions emitted `pull_request_writable=false` for fork heads but still launched the same privileged `opencode github run` step used for writable branches. The distinction existed only in the prompt.

That was not an enforceable security boundary. GitHub-mode OpenCode can exchange the job's OIDC identity for an OpenCode GitHub App token. A model error, indirect prompt injection, or implementation defect could therefore create comments, commits, branches, pull requests, or workflow reruns even though the prompt said the fork was read-only.

## Decision

Split hourly execution into three top-level jobs with different authority:

1. **`select-loop`** validates complete live queue metadata under read-only `contents`, `issues`, and `pull-requests` permissions. It emits exact-head/base/writeability data as job outputs and has no `id-token` permission.
2. **`fork-read-only`** runs only when maintenance mode is selected and `pull_request_writable == 'false'`. It has read-only GitHub permissions, no `id-token`, and no repository-write permission. A separate evidence-collection step uses the job's read-scoped `GITHUB_TOKEN` to persist PR metadata, files, reviews, comments, checks, statuses, workflow runs, and patch data into local evidence files. The model step receives only the NVIDIA model credential and invokes `opencode run --auto`, not GitHub mode. It receives no GitHub token, OIDC variables, write API, workflow-rerun authority, or branch publication path.
3. **`write-loop`** owns repository mutation and product delivery. Its GitHub-mode maintenance step is structurally conditioned on `pull_request_writable == 'true'`. Only this job has `id-token: write` and repository write permissions.

The fork model can analyze the protected default branch and collected local evidence, but it cannot publish a comment or repair. Its output remains a read-only job log. A later writable repository-owned task may address an integration problem without mutating the fork head.

The workflow additionally rechecks live fork head evidence during collection. A changed head does not authorize mutation; it only changes the local evidence being analyzed.

## Security invariants

- A fork decision cannot reach `opencode github run`.
- The fork job has no `id-token` key.
- `actions`, `checks`, `contents`, `issues`, `pull-requests`, `security-events`, and `statuses` are read-only in the fork job.
- No GitHub token is present in the fork model step.
- GitHub access occurs only in the preceding deterministic evidence-collection step.
- The write-capable maintenance step requires `needs.select-loop.outputs.pull_request_writable == 'true'` in its workflow condition.
- Prompt text remains defense in depth and is never the sole enforcement mechanism.

## Consequences

### Positive

- Fork read-only behavior is enforced by GitHub job permissions, OIDC absence, command selection, and step conditions rather than model compliance.
- Indirect prompt injection in a fork diff or comment cannot obtain repository write authority through the model step.
- The scheduler still performs useful triage rather than treating a fork as a blanket no-op.
- Writable same-repository maintenance and product work retain their existing exact-head repair capabilities.
- The gate itself classifies untrusted queue metadata before any write-capable job starts.

### Negative

- The workflow duplicates checkout and verified OpenCode installation across read-only and write jobs.
- Fork triage cannot leave a durable GitHub comment because that would require write authority; evidence is limited to workflow logs unless a separate trusted control-plane process republishes it.
- `opencode run --auto` and `opencode github run` now require separate operational tests.
- Multi-job scheduling adds startup latency and GitHub Actions consumption.

## Verification

`tests/test_fork_read_only_scheduler_contract.py` must prove:

- the write-capable maintenance step includes the exact writable condition;
- the fork path is a separate job with read-only permissions and no `id-token`;
- the fork model uses `opencode run --auto`, never GitHub mode;
- the fork model step contains no GitHub token or OIDC request variable;
- read-scoped GitHub evidence collection precedes model execution;
- the selector job has no repository write permission.

The full workflow, security, continuation, supply-chain, and repository contract suites remain required at 100% production statement and branch coverage.

## Affected artifacts

- `.github/workflows/hourly-product-gap.yml`
- `tests/test_fork_read_only_scheduler_contract.py`
- `tests/test_workflow_contracts.py`
- `docs/adr/README.md`
- `docs/SECURITY.md`
- `docs/THREAT_MODEL.md`
- `docs/OPERABILITY.md`
- `docs/TEST_STRATEGY.md`
- `CHANGELOG.md`
