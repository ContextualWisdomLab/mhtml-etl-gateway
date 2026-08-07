# ADR 0007: Hourly bounded product-development loop

**Status:** Accepted
**Date:** 2026-08-07

## Context

The repository requires continuous product work without overlapping agents, duplicate PRs, public model sessions, or a second merge scheduler. Scheduled work must use NVIDIA NIM rather than Copilot credentials.

## Decision

A default-branch-only hourly workflow:

- collects current open PR and `agent-task` issue evidence;
- requires `NVIDIA_NIM_API_KEY`;
- stops when any PR is open;
- resumes exactly one durable task or creates one when none exists;
- fails closed when multiple or malformed task leases exist;
- invokes a full-SHA-pinned OpenCode GitHub Action with `share: false`;
- grants scoped contents/issues/pull-request write permissions only to the development job;
- instructs the agent to use TDD, update documentation, run complete verification, create at most one PR, and never merge or release.

Central `.github` required workflows remain the only review/security/merge authority.

## Consequences

A failed run can resume from the durable issue without duplicate branches. Work is bounded by an open-PR gate. Public session sharing is structurally disabled. Review and check latency does not authorize a bypass.
