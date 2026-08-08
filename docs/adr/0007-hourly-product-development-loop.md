# ADR 0007: Hourly autonomous maintenance and product-development loop

**Status:** Accepted
**Date:** 2026-08-08

## Context

The first scheduler treated any open pull request as a reason to stop. That protected against duplicate PRs, but it also converted the repository's most important work queue into a permanent no-op while reviews, checks, or correctable defects were outstanding. The prompt could record a blocker but had no explicit requirement to find the root cause, prove that a remedy was technically possible, or execute repository-owned recovery.

The organization central `.github` workflows already own independent review, security evidence, branch freshness, and guarded merge. A repository scheduler must therefore repair and verify work without becoming a second approval or merge controller.

## Root cause

- The gate modeled open PRs as exclusion state rather than actionable maintenance state.
- It did not emit a validated exact-head/base lease or distinguish same-repository from fork heads.
- The workflow lacked check-read and bounded Actions-rerun permissions.
- The agent prompt did not separate code defects, transient infrastructure, stale evidence, external approval dependencies, and conflicts.
- “Report the blocker” was permitted even when a practical repository-owned action existed.

## Decision

A protected-default-branch hourly workflow now selects exactly one of two modes:

1. `maintain_pull_request`: validate the complete open-PR inventory, choose the lowest-numbered PR deterministically, and emit its exact head SHA, head ref, base ref, writeability, and queue size.
2. `develop_product_gap`: only when no PR is open, resume exactly one durable `agent-task` issue or create one.

PR maintenance requires root-cause analysis before mutation. Every blocker is classified as an actionable repository defect, transient infrastructure failure, stale or superseded evidence, external policy or independent-approval dependency, or merge conflict. The agent must prove the proposed action is possible with available permissions, APIs, credentials, and branch ownership and that it can change the blocker.

Before every write, the agent re-fetches the live head and relevant target state. A changed lease discards stale work. Same-repository defects are fixed test-first on the existing PR branch. Fork heads remain read-only. Failed or cancelled GitHub Actions jobs may be rerun only after proving the failure is transient and no source fix is required; queued or pending work is neither rerun nor counted as passing. Independent approval is never synthesized. If only an external dependency remains, one deduplicated blocker record is preserved and the next buyer-visible gap may be refined in one durable issue, but no second PR is opened.

The workflow uses NVIDIA NIM, `share: false`, full-SHA action pins, and scoped permissions. It never merges, enables auto-merge, approves, tags, publishes, or releases. Central `.github` required workflows remain the sole review/security/merge authority.

## Consequences

- An open PR causes useful maintenance rather than disabling the loop.
- Multiple PRs are drained deterministically one per run without parallel writers.
- The scheduler can repair code and retry genuinely transient jobs while preserving exact-head evidence.
- External review and policy limits remain visible and cannot be bypassed.
- Product development stays single-flight because a new product PR is allowed only after the open PR queue reaches zero.
- The workflow becomes active only after the commit containing it reaches the protected default branch.
