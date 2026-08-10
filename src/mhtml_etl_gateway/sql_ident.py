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
