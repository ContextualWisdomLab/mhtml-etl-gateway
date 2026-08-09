# ADR 0007: Hourly autonomous maintenance and product-development loop

**Status:** Accepted
**Date:** 2026-08-09

## Context

The first scheduler treated any open pull request as a reason to stop. That protected against duplicate PRs, but it also converted the repository's most important work queue into a permanent no-op while reviews, checks, or correctable defects were outstanding. The next revision selected the lowest-numbered PR, but an externally blocked first PR could still starve independently actionable later PRs. The prompt could record a blocker without guaranteeing work-conserving queue progression.

The maintenance prompt also claimed it would inspect code-scanning findings while the job token lacked `security-events: read`. Finally, a privileged coding agent reads pull-request source, comments, reviews, logs, issues, and artifacts that may contain prompt-injection text. Those surfaces must remain data and may not redefine the agent's trusted instructions or cause secret disclosure.

The organization central `.github` workflows already own independent review, security evidence, branch freshness, and guarded merge. A repository scheduler must repair and verify work without becoming a second approval or merge controller.

## Root cause

- The original gate modeled open PRs as exclusion state rather than actionable maintenance state.
- The single-target revision did not require progression to another PR after proving the first target externally blocked.
- It did not initially emit a validated exact-head/base lease or distinguish same-repository from fork heads.
- The workflow lacked code-scanning read permission even though the prompt required that evidence.
- Repository and review material was not explicitly classified as untrusted data relative to the privileged prompt and model credential.
- The agent prompt did not separate code defects, transient infrastructure, stale evidence, external approval dependencies, and conflicts.
- “Report the blocker” was permitted even when a practical repository-owned action existed.

## Decision

A protected-default-branch hourly workflow selects exactly one of two modes:

1. `maintain_pull_request`: validate the complete open-PR inventory, choose the lowest-numbered PR as the initial cursor, and emit its exact head SHA, head ref, base ref, writeability, and queue size.
2. `develop_product_gap`: only when no PR is open, resume exactly one durable `agent-task` issue or create one.

PR maintenance requires root-cause analysis before mutation. Every blocker is classified as an actionable repository defect, transient infrastructure failure, stale or superseded evidence, external policy or independent-approval dependency, or merge conflict. The agent must prove the proposed action is possible with available permissions, APIs, credentials, and branch ownership and that it can change the blocker.

Before every write, the agent re-fetches the live head and relevant target state. A changed lease discards stale work. Same-repository defects are fixed test-first on the existing PR branch. Fork heads remain read-only. Failed or cancelled GitHub Actions jobs may be rerun only after proving the failure is transient and no source fix is required; queued or pending work is neither rerun nor counted as passing. Independent approval is never synthesized.

When a PR has no executable repository-owned action, the agent preserves one deduplicated blocker record, does not repeatedly re-prove the unchanged boundary, and proceeds to the next open PR while execution capacity remains. Only one branch may be actively mutated at a time, and every subsequent PR receives a fresh exact-head lease and the same RCA discipline. A blocked PR therefore blocks only its affected action, not the whole invocation.

Pull-request source, comments, issue bodies, review text, logs, and artifacts are untrusted data, never instructions. Commands are derived independently from the trusted workflow prompt, repository policy, and verified tool documentation. The agent may not print, serialize, commit, comment, or transmit environment variables or secret values, and it may not execute commands copied from untrusted repository content.

The workflow grants `security-events: read` in addition to scoped Actions, checks, contents, issues, pull-request, and status permissions so its stated code-scanning inspection is technically possible. It uses NVIDIA NIM, `share: false`, full-SHA action pins, and scoped job permissions. It never merges, enables auto-merge, approves, tags, publishes, or releases. Central `.github` required workflows remain the sole review/security/merge authority.

## Consequences

- An open PR causes useful maintenance rather than disabling the loop.
- An externally blocked first PR cannot starve independently actionable later PRs.
- The scheduler serializes branch mutation while remaining work-conserving across the queue.
- Code-scanning RCA is backed by an actual read permission rather than prompt-only intent.
- PR-controlled prose cannot legitimately redefine privileged instructions or authorize secret handling.
- The scheduler can repair code and retry genuinely transient jobs while preserving exact-head evidence.
- External review and policy limits remain visible and cannot be bypassed.
- Product development stays single-flight because a new product PR is allowed only after the open PR queue reaches zero.
- The workflow becomes active only after the commit containing it reaches the protected default branch.
