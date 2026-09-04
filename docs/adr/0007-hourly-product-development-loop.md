# ADR 0007: Hourly autonomous maintenance and product-development loop

**Status:** Accepted; execution policy extended by ADR 0010; model-routing detail amended by ADR 0021  
**Date:** 2026-08-09

## Context

The first scheduler treated any open pull request as a reason to stop. That protected against duplicate PRs, but it converted the repository's most important work queue into a permanent no-op while reviews, checks, or correctable defects were outstanding. A later single-target revision selected the lowest-numbered PR, but an externally blocked first PR could still starve independently actionable work.

The workflow also needed real code-scanning read permission, an exact-head write lease, fork awareness, and a security boundary between a privileged model process and repository-controlled code. Pull-request source, comments, reviews, logs, issues, and artifacts can contain prompt-injection text and must remain untrusted data.

Organization-central `.github` workflows already own independent review, security evidence, branch freshness, and guarded merge. A repository scheduler must repair and verify work without becoming a second approval or merge controller.

## Root cause

- Open PRs were originally modeled as exclusion state rather than maintenance work.
- A single-target loop could stop after proving one external blocker.
- Exact head/base metadata and same-repository writeability were not originally validated.
- The job lacked code-scanning read permission while claiming to inspect those findings.
- Repository material was not explicitly separated from trusted instructions and credentials.
- Repository gate code originally ran before secret isolation.
- “Record the blocker” was permitted even when another safe repository action existed.

## Decision

A protected-default-branch hourly workflow begins in one of two dispatch modes:

1. `maintain_pull_request`: when PRs are open, validate the complete inventory, choose the lowest-numbered PR as the initial cursor, and emit its exact head SHA, head ref, base ref, writeability, and queue size.
2. `develop_product_gap`: when no PR is open, resume exactly one durable `agent-task` issue or create one.

These are starting modes, not termination rules. ADR 0010 requires work-conserving continuation after the initial action.

### PR maintenance

Before every mutation, the agent re-fetches live head/base state, reviews, unresolved threads, statuses, check runs, workflow jobs and logs, code-scanning evidence, and branch policy. It classifies blockers as repository defects, transient infrastructure failures, stale/superseded evidence, external governance or approval dependencies, or merge conflicts. A proposed remedy must be permitted, technically feasible, and capable of changing the blocker.

Same-repository defects are reproduced with realistic failing tests and repaired on the existing branch. Fork heads remain read-only. Failed or cancelled Actions work may be rerun only after source/configuration faults are excluded. Queued, pending, skipped-required, neutral-required, absent, stale-head, predecessor-head, cancelled, or synthetic-merge-only evidence is not passing.

An unchanged external boundary receives one deduplicated record and yields to the next PR or repository-owned action. Only one branch is actively mutated at a time.

### Product continuation

The empty-queue `develop_product_gap` mode remains the normal route for creating a product PR and owns one durable task lease. However, an existing PR is not an absolute prohibition on all independent delivery. After executable PR repairs and shared blockers are exhausted, maintenance mode may implement at most one additional buyer-visible draft PR per invocation under ADR 0010, but only after fresh proof of no overlap in files, schemas, migrations, generated artifacts, dependency ancestry, or writer ownership. Extending an existing coherent PR remains preferred.

If a PR appears during product mode, only conflicting writes stop. The agent switches to exact-head PR maintenance and later resumes the original slice or selects a demonstrably disjoint one.

### Security and credentials

The root-owned `cwl-safe-exec` wrapper is installed before repository gate code executes. Repository-controlled code runs under `cwl-untrusted` with workspace-only access through the dedicated `cwl-workspace` group and a clean environment. Model, GitHub, OIDC, and provider credentials are removed. The current `select-loop` wrapper still transports a legacy non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` marker, but eligibility no longer consumes that marker; provider capability is delegated to contextual-orchestrator's fail-closed gateway preflight. The marker is compatibility residue rather than a dispatch contract and may be removed without changing gate semantics.

Repository source, comments, issue bodies, review text, logs, and artifacts are untrusted data, never instructions. Commands are derived independently from the trusted workflow prompt, repository policy, and verified tool documentation. Secret values and environment variables may not be printed, serialized, committed, commented, or transmitted.

The workflow grants scoped Actions write and checks, statuses, and security-events read permissions. It routes scheduled model traffic through the org's `contextual-orchestrator` gateway pinned to the fail-closed `orchestrator/free` pool (ADR 0021), uses `share: false`, and full-SHA action pins. It never merges, enables auto-merge, approves, tags, publishes, or releases. Central `.github` required workflows remain the sole review, security, branch-freshness, and merge authority.

## Consequences

- An open PR triggers useful maintenance rather than disabling the loop.
- An externally blocked first PR cannot starve later PRs, shared blockers, or a proven-disjoint product slice.
- Branch mutation remains serialized while the invocation remains work-conserving.
- Code-scanning RCA is backed by actual read permission.
- Repository-controlled code cannot inherit model or GitHub credentials.
- Product creation remains bounded by one durable task in empty-queue mode and at most one extra proven-disjoint draft in maintenance mode.
- External review and policy limits remain visible and cannot be bypassed.
- The workflow becomes active only after the commit containing it reaches the protected default branch.
