# AGENTS.md

## Development Rules

- Preserve raw MHTML artifacts immutably.
- Never execute embedded scripts or active HTML content.
- Database objects use multiword snake_case names.
- Every transformation must preserve lineage.
- Parsing failures fail closed.
- Add tests before production behavior changes.
- Maintain complete documentation and CHANGELOG entries.
