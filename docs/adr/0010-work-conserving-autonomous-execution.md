# ADR 0010: Work-conserving autonomous execution

**Status:** Accepted  
**Date:** 2026-08-09

## Context

Earlier scheduler revisions improved PR maintenance but still permitted a run to end after one patch, one PR publication, one queued check, one review delay, one externally blocked merge, or even a scheduler-prompt update. That behavior left safe repository-owned work undone and made the hourly recurrence compensate for avoidable early termination.

A repository can contain several independent work classes at once: actionable review defects, failed checks, externally blocked PRs, shared CI or documentation defects, release-readiness gaps, unresolved issues, buyer-visible product gaps, and ecosystem integration work. A blocker in one class does not prove that the remaining classes are blocked.

## Decision

### Success invariant

Success means **material repository progress**, not status narration. Inventory collection, blocker restatement, prompt editing, issue grooming, check waiting, and a single mutation are intermediate activities. A run that ends after one such activity while another safe executable action exists is failed execution.

The hourly recurrence is continuation, not deferral. Feasible work that fits the current invocation is not intentionally saved for the next hourly run. Updating the scheduler or its prompt never constitutes a normal end condition; the loop immediately resumes the live executable queue.

### Execution cycle

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

Routine output is empty. A completed patch, published PR, prompt update, queued check, review delay, rate limit, provider cooldown, or external approval dependency never terminates the invocation while another safe repository-owned action exists.

The executable queue is ordered as follows:

1. current-head product, security, test, and review defects;
2. demonstrably transient failed or cancelled jobs;
3. the next open PR;
4. shared CI, tooling, dependency, standards, and documentation blockers;
5. issue closure and documentation/architecture/operability/traceability completeness;
6. release-readiness work that does not bypass protected release authority;
7. one buyer-visible product slice that is demonstrably disjoint from active PR work;
8. high-leverage CWL ecosystem integration that preserves standalone operation;
9. read-only preparation only when no safe mutation remains.

A blocked action blocks only that action. An unchanged external boundary receives one deduplicated record and yields to the next item. A gate-clean PR owned by central merge automation does not cause the repository loop to wait.

### Valid stop conditions

The loop may stop only when either:

1. the finite execution budget is genuinely exhausted after completing as much safe work as possible; or
2. a fresh full-queue scan proves every remaining item is non-actionable under current authority because it requires external permission or governance, conflicts with another live writer, or would be unsafe.

Before such a stop, exact evidence and the next executable action are persisted in the durable task or affected PR. A user-facing recap does not substitute for that durable continuation state.

### Post-PR continuation

When the open PR queue reaches zero, or only externally blocked PR actions remain, the same invocation immediately continues through unresolved issues, document and ADR completeness, release readiness, buyer-visible product gaps, and ecosystem integration. Closing an issue, handing a PR to central merge automation, publishing a commit, creating a PR, or updating this prompt remains an intermediate event.

Open PRs are not an absolute ban on independent delivery. After all executable PR repairs and shared blockers are exhausted, the agent may create at most one additional draft PR per invocation only after a fresh proof of no overlap in files, schemas, migrations, generated artifacts, dependency ancestry, and writer ownership. The PR must be based on the live intended base and pass the complete repository suite. Extending an existing coherent PR remains preferred.

If a PR appears during product mode, only conflicting writes stop. The loop switches to exact-head PR maintenance and later resumes the slice or selects a demonstrably disjoint one.

The agent does not ask the user for routine next steps or confirmations that live repository evidence can resolve. Escalation is reserved for a concrete external permission or governance action, or an irreconcilable product, scientific, or security decision, when it is the sole remaining blocker and no other safe work remains.

The scheduler still never approves, enables auto-merge, merges, tags, publishes, or releases. Those actions remain owned by organization-central protected workflows.

## Security boundary

Repository-controlled code runs only through the root-owned `cwl-safe-exec` wrapper under the dedicated `cwl-workspace` group. The wrapper is installed before the repository gate executes. The gate receives only the non-secret `NVIDIA_NIM_API_KEY_CONFIGURED` marker; model, GitHub, OIDC, and provider credentials are removed from the unprivileged environment.

## Consequences

- Hourly recurrence becomes continuation rather than recovery from voluntary early termination.
- Prompt or scheduler maintenance cannot consume an invocation and terminate it by itself.
- Review and check latency no longer idles the repository.
- One externally blocked PR cannot starve another PR, documentation work, release preparation, ecosystem work, or a proven-disjoint product slice.
- PR count remains bounded by explicit non-overlap and one-additional-draft limits.
- Routine narration no longer consumes execution capacity.
- Stop conditions are narrow, testable, and based on a fresh full-queue scan.
- Central merge protections and independent approval remain intact.
