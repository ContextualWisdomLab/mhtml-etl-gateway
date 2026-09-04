# ADR 0021: Route scheduled model traffic through the org's contextual-orchestrator gateway

**Status:** Accepted; amends the model-routing detail of ADR 0007
**Date:** 2026-09-02

## Context

The hourly workflow called `nvidia-nim/nvidia/llama-3.3-nemotron-super-49b-v1.5` directly through
OpenCode's built-in `nvidia-nim` provider, using `NVIDIA_NIM_API_KEY` as the sole provider
credential in all three of its OpenCode invocations. An org-wide audit (2026-09-02, tracked in
`ContextualWisdomLab/mhtml-etl-gateway#60`) found this bypassed the organization's central LLM
gateway (`ContextualWisdomLab/contextual-orchestrator`), which every other governed CWL workflow
now routes through, fail-closed, at the `orchestrator/free` pool. The org owner has repeatedly
directed that every GitHub Actions workflow operate via `orchestrator/free`.

Two existing patterns already vendor `contextual-orchestrator` into a consumer workflow:

- `ContextualWisdomLab/.github`'s `scripts/ci/contextual_orchestrator_review_sidecar.sh` clones a
  pinned commit, installs its hash-pinned `requirements.lock`, and drives a bespoke
  `contextual_orchestrator_review_launcher.py` built for one-shot Strix/OpenCode/Noema PR review
  passes (bounded route-preflight catalog, ZDR routing evidence, account-capped agent selection).
  That apparatus answers review-specific auditability requirements this repository does not have.
- `ContextualWisdomLab/contextual-orchestrator`'s own `.github/workflows/opencode-hourly-loop.yml`
  is the structurally closer analog: a long-running, write-capable OpenCode CLI loop that starts
  the gateway in-process via `python -m scripts.ci.serve_seeded_gateway --serve
  --auto-discover-model-agents --auth-token-key CONTEXTUAL_ORCHESTRATOR_TOKEN`, waits for
  `/healthz`, and points OpenCode's config at the gateway's `orchestrator/*` virtual model IDs.

`orchestrator/free` and `orchestrator/auto` are first-class virtual model IDs implemented inside
`contextual_orchestrator.orchestrator.TaskOrchestrator` (`FREE_MODEL`/`AUTO_MODEL`) — routing to
only free-priced discovered agents is core gateway behavior, not something a caller-side catalog
file has to construct. This was confirmed by running `scripts/ci/serve_seeded_gateway.py` locally
against a pinned checkout: with zero provider credentials seeded, a `/v1/chat/completions` request
for `orchestrator/free` returns `HTTP 400 {"error_code": "invalid_model", "error_message": "no
enabled zero-cost model is available"}` rather than a silent fallback — the fail-closed contract
the org requires.

`.github`'s own sidecar pin (`045d17da5e2aea56a97e241ee158ab1628d78660`, 2026-08-31) predates the
`SERVER_AUTH_ENV_NAME`/`--auth-token-key` bootstrap that `serve_seeded_gateway.py` needs for this
integration; that pin was never exercised against this entrypoint. This repository therefore pins
independently, to a commit verified locally to support it.

## Decision

The hourly workflow adds one new step per job that needs a model
(`Provision contextual-orchestrator gateway sidecar`), inserted after the verified OpenCode CLI
install and before the OpenCode invocation:

1. Requires at least one of the five org provider secrets (`BYTEZ_API_KEY`, `NVIDIA_NIM_API_KEY`,
   `NVIDIA_NIM_API_KEY_SUB`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`); individual secrets remain
   optional, matching the `.github` sidecar's own admission contract.
2. Generates and masks an ephemeral loopback bearer token.
3. Clones `ContextualWisdomLab/contextual-orchestrator` at pinned commit
   `8839081659df587b19642be17b9114f9dee8b666`, verifies the checked-out `HEAD` matches the pin, and
   installs its `requirements.lock` with `pip install --require-hashes --no-deps`.
4. Starts `python -m scripts.ci.serve_seeded_gateway --serve --auto-discover-model-agents
   --auth-token-key CONTEXTUAL_ORCHESTRATOR_TOKEN` bound to `127.0.0.1:18080`, seeded from the
   present provider secrets.
5. Waits for `/healthz`, then performs one real `orchestrator/free` `/v1/chat/completions`
   preflight before treating the gateway as ready — `/healthz` alone does not prove the pool can
   actually serve a completion (see `.github`'s own 2026-08-30 sidecar incident history for the
   class of failure this guards against). This preflight is a single attempt with no retry —
   simpler than `.github`'s bounded-retry gateway preflight, since this workflow does not carry
   that sidecar's Strix-specific reliability requirements yet.
6. Exports `CONTEXTUAL_ORCHESTRATOR_TOKEN` via `$GITHUB_ENV` for the job's remaining steps.

`opencode.jsonc` now declares a `contextual_orchestrator_gateway` provider (`@ai-sdk/openai-compatible`,
`baseURL: http://127.0.0.1:18080/v1`, `apiKey: {env:CONTEXTUAL_ORCHESTRATOR_TOKEN}`) exposing model
`orchestrator/free`, and `model`/`small_model` both target
`contextual_orchestrator_gateway/orchestrator/free`. All three OpenCode invocation steps set
`MODEL: contextual_orchestrator_gateway/orchestrator/free` and no longer receive a raw provider API
key directly — that credential now reaches only the short-lived sidecar-provisioning step, not the
long-running, PR-content-processing OpenCode agent process. This narrows the credential's exposure
window in `fork-read-only`, the job that processes untrusted fork PR content, compared to the prior
design where the raw `NVIDIA_NIM_API_KEY` sat in that same agent process's environment for the
run's full duration.

The `cwl-safe-exec` wrapper in `write-loop` additionally strips `NVIDIA_NIM_API_KEY_SUB`,
`BYTEZ_API_KEY`, `OPENROUTER_API_KEY`, and `CONTEXTUAL_ORCHESTRATOR_TOKEN` (alongside the
credentials it already stripped) before repository-controlled code executes.

No repository-specific model-fallback list or system-prompt tuning rode on the direct NVIDIA call;
the three prompts are provider-agnostic and are unchanged by this migration.

## Consequences

### Positive

- Scheduled model traffic is governed, auditable, and fail-closed like every other CWL workflow,
  closing the gap `ContextualWisdomLab/mhtml-etl-gateway#60` recorded.
- The raw provider credential's exposure window narrows, most importantly in the untrusted-content
  fork-triage job.
- The vendoring mechanism directly reuses `contextual-orchestrator`'s own hourly-loop entrypoint
  instead of introducing a third bespoke launcher.

### Negative

- Every eligible run now also clones and pip-installs `contextual-orchestrator` before the agent
  can start, adding runtime and one more upstream dependency surface.
- This repository's pin (`8839081...`) is independent of `.github`'s (`045d17da...`); the two must
  be tracked and upgraded separately until `.github`'s sidecar also depends on the
  `--auth-token-key` bootstrap and the two can reasonably converge.
- The completion preflight is single-attempt; a transient gateway 5xx fails the run rather than
  retrying (see the `ponytail:` comment at the preflight call site for the upgrade path).

## Affected artifacts

- `.github/workflows/hourly-product-gap.yml`
- `opencode.jsonc`
- `tests/test_workflow_contracts.py`
- `tests/test_opencode_runner_supply_chain.py`
- `tests/test_fork_read_only_scheduler_contract.py`
- `AGENTS.md`
- `docs/adr/0007-hourly-product-development-loop.md`
- `docs/OPERABILITY.md`
- `docs/VALIDATION_REPORT.md`
- `docs/SECURITY.md`
- `CHANGELOG.md`
