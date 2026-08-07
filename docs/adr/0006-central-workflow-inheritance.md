# ADR-0006: Inherit central review and merge workflows

**Status:** Accepted

## Decision

Use the active organization required-workflow ruleset in `ContextualWisdomLab/.github` for review, security, branch freshness, and guarded merge. Do not copy or schedule a repository-local merge controller.

## Consequences

Governance fixes have organization-wide leverage and the repository avoids duplicate runs. Product-specific test/build and hourly product-development workflows remain local.
