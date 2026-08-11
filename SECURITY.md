# Security Policy

## Supported versions

The project is pre-1.0. Security fixes apply to the protected default branch and to the latest published release once releases begin.

## Reporting

Do not open public issues containing customer MHTML, credentials, PII, internal file locations, exploit payloads, or infrastructure details. Use GitHub private vulnerability reporting for this repository or the ContextualWisdomLab security contact.

Include the affected commit, exact parser or future loader path, a minimized synthetic reproduction, impact, and recommended containment. Remove customer values while preserving the structural defect.

## Security boundary

The parser never renders HTML, executes active content, resolves XML external entities, launches browser or office software, or performs network retrieval. It validates MIME structure and root-selection metadata before decoding the selected root. Expected malformed-input failures use stable error codes and generic, nonreflecting messages.

Default reports omit every cell-derived value and replace raw Content-Location with scheme plus SHA-256. Header values are available only through explicit local opt-in and inherit the source artifact's protection requirements.

See [docs/SECURITY.md](docs/SECURITY.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).
