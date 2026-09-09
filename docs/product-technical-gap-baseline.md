# Product–Technical Gap Baseline

This baseline records code-current gaps and acceptance evidence for `mhtml-etl-gateway`.

## PostgreSQL legacy-table lookup

`PostgresSink._reject_legacy_table_split()` checks a bounded set of candidate table names before permitting a schema transition. The protected implementation built only `%s` placeholder tokens into the SQL text and passed all candidate names separately as bound values; no table name was interpolated as SQL. Bandit B608 therefore does not by itself establish a SQL-injection defect.

PR #81 changes the lookup to PostgreSQL `= ANY(%s)` and supplies the names as a Python list. Psycopg 3 documents this as the native parameterized collection form and adapts Python lists to PostgreSQL arrays. The value/SQL boundary remains explicit and the query text no longer needs a generated placeholder sequence.

### Invariants

- Candidate table names are SQL values, not identifiers; they remain bound parameters.
- Dynamic SQL identifiers, if ever required, must use Psycopg SQL composition rather than f-strings or value placeholders.
- The legacy-table rejection semantics and deterministic candidate ordering remain unchanged.
- A static-analysis warning is not promoted to a vulnerability severity without a controllable SQL-text path and a realistic exploit reproduction.

### Acceptance

- exact-head tests preserve legacy table discovery/rejection behavior;
- Bandit/security/static checks are evaluated on the same exact head;
- current-head independent review is required before Ready/merge;
- the PR remains a database-query refactor unless new exploit evidence demonstrates a security defect.
