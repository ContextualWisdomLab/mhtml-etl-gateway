# Product / technical gap baseline

Status: Draft — exact-head verification pending

## Current product boundary

`mhtml-etl-gateway` owns bounded MHTML inspection, schema proposal/governance handoff, and optional transactional PostgreSQL loading. PostgreSQL identifiers are validated separately from data values; candidate legacy table names are values and must stay in the parameter-binding boundary.

## Buyer-visible gap

The released `0.4.0` implementation safely bound each legacy-table candidate value, but varied the SQL text by constructing an `IN (%s, ...)` placeholder list. Bandit B608 could not establish that the interpolated fragment consisted only of generated placeholders. The finding was therefore a scanner false positive rather than evidence of exploitable SQL injection, but the variable query shape imposed avoidable audit and maintenance cost.

PR #42 originally documented an `= ANY(%s)` repair without containing the production change. That documentation-only state was repaired rather than closed: the PR branch was non-force restacked on released `main`, its unique journal delta was preserved, and an executable contract was added before the production change.

## Decision

- Keep legacy candidate values parameterized; never interpolate candidate names into SQL text.
- Use one fixed query: `table_name = ANY(%s)`.
- Pass one Python `list` inside the DB-API parameter sequence. Psycopg 3 adapts Python lists to PostgreSQL arrays and explicitly recommends `= ANY(%s)` for a list of candidate values.
- Preserve sorted candidate ordering so diagnostic/test evidence is deterministic.
- Treat this as query-shape hardening and static-analysis clarity, not as remediation of a demonstrated SQL-injection vulnerability.

Rejected alternatives:

- Retain the generated `IN (%s, ...)` text and suppress B608: safe value binding remains difficult for scanners/reviewers to establish and the dynamic text is unnecessary.
- Interpolate literal candidate names: violates the data-value parameter boundary and would create a real injection risk.
- Pass a tuple as the single `ANY` parameter: Psycopg 3 documents a Python list, not a tuple, for PostgreSQL array adaptation in this use case.
- Close the documentation-only PR: it contained a valid intended delta that was not superseded; repair and non-force restack preserve its lineage.

## TDD / exact evidence

- Non-force reconciliation commit `617e7f6f3c49dd8f0779e08adfbc2c6127643250` combines the previous PR head with released `main@779254927abb1e7cee80fd949907ccd03f9fc7be` and corrects the journal claim without discarding either history.
- Test-first commit `7292ec553fd72ed03f819f75e8f66eecb51e7242` adds a contract requiring fixed `= ANY(%s)` SQL and one bound list parameter. The pre-repair source still used generated `IN` placeholders, so this contract describes a real behavioral delta; no hosted RED result is claimed unless an exact-head run records it.
- Causal production commit `4c63be22c742fe8cf1fc0331ca2b5378468f1b1a` replaces generated placeholders with the fixed query and list binding.
- Compatibility-test commit `19e0bc261ce92170c676ef90a32a66f4cf8e265d` updates the existing boundary-candidate assertion to inspect the new single-array envelope rather than the old flattened parameter tuple.
- `CHANGELOG.md` records the unreleased query-shape change. Current-head CI/security/review evidence remains authoritative; predecessor success does not transfer after documentation or test commits move the head.

## Primary-source traceability

Psycopg Team. (2026). *Adapting basic Python types — Psycopg 3 documentation*. https://www.psycopg.org/psycopg3/docs/basic/adapt.html

The Psycopg 3 documentation states that Python lists are adapted to PostgreSQL arrays and recommends `= ANY(%s)` with a list instead of trying to bind a collection to `IN`.

Psycopg Team. (2026). *Differences from psycopg2 — Psycopg 3 documentation*. https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html

The migration documentation likewise specifies `= ANY()` plus a Python list for candidate collections and notes that it also handles an empty list, unlike an empty SQL `IN ()` expression.

## Remaining acceptance

The unchanged current PR head must run the repository's tests, coverage, security/SAST and then-live required workflows to terminal success. The regression must prove both the SQL text and the parameter envelope; a scanner success without the unit contract is insufficient. Fresh review must contain no valid unresolved finding, and only then may normal protected merge/release decisions proceed.
