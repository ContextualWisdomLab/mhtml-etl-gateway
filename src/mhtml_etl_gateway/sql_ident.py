"""Safe PostgreSQL identifier validation (no dynamic SQL injection surface)."""

from __future__ import annotations

import re

# Only multiword snake_case identifiers produced by schema_inference.
_SAFE_IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class UnsafeIdentifierError(ValueError):
    """Rejected identifier that is not a safe snake_case name."""


def require_safe_ident(name: str) -> str:
    """Return ``name`` if it is a safe SQL identifier, else raise."""
    if not isinstance(name, str) or not _SAFE_IDENT.match(name):
        raise UnsafeIdentifierError(f"unsafe SQL identifier: {name!r}")
    return name


def quote_sql_literal(value: str) -> str:
    """Quote a PostgreSQL string literal for generated, parameter-free DDL.

    ``COMMENT ON`` is emitted as part of offline DDL, so the comment cannot be
    passed as a bind parameter.  Escape-string syntax makes backslashes and
    quotes data rather than SQL syntax.  PostgreSQL text values cannot contain
    NUL bytes, so reject those rather than producing invalid DDL.
    """
    if not isinstance(value, str):
        raise TypeError("SQL literal value must be a string")
    if "\x00" in value:
        raise ValueError("SQL literal cannot contain NUL bytes")
    escaped = (
        value.replace("\\", "\\\\")
        .replace("'", "''")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f"E'{escaped}'"
