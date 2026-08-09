# ADR 0010: Work-conserving autonomous execution

**Status:** Accepted  
**Date:** 2026-08-09

## Context

Earlier scheduler revisions improved PR maintenance but still permitted a run to end after one patch, one PR publication, one queued check, one review delay, or one externally blocked merge. That behavior left safe repository-owned work undone and made the hourly recurrence compensate for avoidable early termination.

A repository can contain several independent work classes at once: actionable review defects, failed checks, externally blocked PRs, shared CI or documentation defects, and buyer-visible product gaps. A blocker in one class does not prove that the remaining classes are blocked.

## Decision

The hourly scheduler is an execution loop rather than a status-reporting loop. It repeatedly performs:

```text
fresh evidence
→ highest-value safe action
→ RCA only as needed
→ realistic failing test
→ minimal mutation
→ exact-head verification
→ central merge handoff
→ next executable item
```

Routine output is empty. A completed patch, published PR, queued check, review delay, rate limit, provider cooldown, or external approval dependency never terminates the invocation while another safe repository-owned action exists.

The executable queue is ordered as follows:

1. current-head product, security, test, and review defects;
2. demonstrably transient failed or cancelled jobs;
3. the next open PR;
4. shared CI, tooling, dependency, standards, and documentation blockers;
5. one buyer-visible product slice that is demonstrably disjoint from active PR work;
6. read-only preparation only when no safe mutation remains.

A blocked action blocks only that action. An unchanged external boundary receives one deduplicated record and yields to the next item. A gate-clean PR owned by central merge automation does not cause the repository loop to wait.

Open PRs are not an absolute ban on independent delivery. After all executable PR repairs and shared blockers are exhausted, the agent may create at most one additional draft PR per invocation only after a fresh proof of no overlap in files, schemas, migrations, generated artifacts, dependency ancestry, and writer ownership. The PR must be based on the live intended base and pass the complete repository suite. Extending an existing coherent PR remains preferred.

If a PR appears during product mode, only conflicting writes stop. The loop switches to exact-head PR maintenance and later resumes the slice or selects a demonstrably disjoint one.

The agent does not ask the user for routine next steps or confirmations that live repository evidence can resolve. Escalation is reserved for a concrete external permission or governance action, or an irreconcilable product, scientific, or security decision, when it is the sole remaining blocker and no other safe work remains.

The scheduler still never approves, enables auto-merge, merges, tags, publishes, or releases. Those actions remain owned by organization-central protected workflows.

## Security boundary

Repository-controlled code runs only through the root-owned `cwl-safe-exec` wrapper under the dedicated `cwl-workspace` group. The wrapper is installed before the repository gate executes. The gate receives only the non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` marker; model, GitHub, OIDC, and provider credentials are removed from the unprivileged environment.

## Consequences

- Hourly recurrence becomes continuation rather than recovery from voluntary early termination.
- Review and check latency no longer idles the repository.
- One externally blocked PR cannot starve another PR or a proven-disjoint product slice.
- PR count remains bounded by explicit non-overlap and one-additional-draft limits.
- Routine narration no longer consumes execution capacity.
- Central merge protections and independent approval remain intact.
