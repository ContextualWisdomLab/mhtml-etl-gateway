"""Deterministic multiword PostgreSQL identifier normalization."""

from __future__ import annotations

import re
import unicodedata

from .identity import sha256_text

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_ACRONYM_BOUNDARY = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")
_UNSAFE_NAME_CHARACTER = re.compile(r"[^\w]+", re.UNICODE)
_MULTI_UNDERSCORE = re.compile(r"_+")

_POSTGRESQL_RESERVED_NAMES = frozenset(
    {
        "all", "analyse", "analyze", "and", "any", "array", "as", "asc",
        "asymmetric", "authorization", "binary", "both", "case", "cast",
        "check", "collate", "collation", "column", "concurrently",
        "constraint", "create", "current_catalog", "current_date",
        "current_role", "current_schema", "current_time", "current_timestamp",
        "current_user", "default", "deferrable", "desc", "distinct", "do",
        "else", "end", "except", "false", "fetch", "for", "foreign",
        "freeze", "from", "full", "grant", "group", "having", "ilike", "in",
        "initially", "inner", "intersect", "into", "is", "isnull", "join",
        "lateral", "leading", "left", "like", "limit", "localtime",
        "localtimestamp", "natural", "not", "notnull", "null", "offset", "on",
        "only", "or", "order", "outer", "overlaps", "placing", "primary",
        "references", "returning", "right", "select", "session_user", "similar",
        "some", "symmetric", "table", "tablesample", "then", "to", "trailing",
        "true", "union", "unique", "user", "using", "variadic", "verbose",
        "when", "where", "window", "with",
    }
)

_HEADER_ALIASES = {
    "mandt": "client_code",
    "guid": "global_identifier",
    "docnosub": "document_subnumber",
    "duedt": "due_date",
    "kunnr": "customer_number",
}
_IDENTIFIER_ALIASES = frozenset({"mandt", "guid", "docnosub", "kunnr"})
_IDENTIFIER_MARKERS = frozenset(
    {
        "id", "identifier", "guid", "uuid", "key", "code", "number", "no",
        "num", "mandt", "kunnr", "docnosub", "client", "customer", "account",
    }
)
_DATE_MARKERS = frozenset(
    {
        "date", "dt", "day", "due", "created", "updated", "valid",
        "effective", "expired", "expiry",
    }
)
_BOOLEAN_MARKERS = frozenset(
    {
        "active", "enabled", "disabled", "deleted", "valid", "flag",
        "indicator", "is", "has", "can",
    }
)


def ordered_semantic_tokens(header: str) -> tuple[str, ...]:
    """Return normalized semantic tokens in deterministic source order."""
    value = unicodedata.normalize("NFKC", header)
    value = _ACRONYM_BOUNDARY.sub("_", value)
    value = _CAMEL_BOUNDARY.sub("_", value)
    value = _UNSAFE_NAME_CHARACTER.sub("_", value).casefold()
    return tuple(item for item in value.split("_") if item)


def semantic_tokens(header: str) -> frozenset[str]:
    """Return set-like normalized tokens for conservative semantic membership tests."""
    return frozenset(ordered_semantic_tokens(header))


def has_identifier_semantics(header: str) -> bool:
    """Return whether a protected header strongly suggests identifier data."""
    ordered_tokens = ordered_semantic_tokens(header)
    tokens = frozenset(ordered_tokens)
    compact = "".join(ordered_tokens)
    return compact in _IDENTIFIER_ALIASES or bool(tokens & _IDENTIFIER_MARKERS)


def has_date_semantics(header: str) -> bool:
    """Return whether a protected header supplies explicit date semantics."""
    ordered_tokens = ordered_semantic_tokens(header)
    tokens = frozenset(ordered_tokens)
    return "".join(ordered_tokens) == "duedt" or bool(tokens & _DATE_MARKERS)


def has_boolean_semantics(header: str) -> bool:
    """Return whether a protected header supplies explicit boolean semantics."""
    return bool(semantic_tokens(header) & _BOOLEAN_MARKERS)


def truncate_identifier(
    identifier: str,
    max_identifier_bytes: int,
    identity_seed: str,
) -> str:
    """Truncate a UTF-8 identifier deterministically with a hash suffix."""
    if len(identifier.encode("utf-8")) <= max_identifier_bytes:
        return identifier
    suffix = "_" + sha256_text(identity_seed)[:10]
    byte_budget = max_identifier_bytes - len(suffix.encode("ascii"))
    prefix = identifier.encode("utf-8")[:byte_budget]
    fallback = "object"[:byte_budget] or "o"
    decoded = prefix.decode("utf-8", errors="ignore").rstrip("_") or fallback
    return decoded + suffix


def normalized_identifier(
    source_name: str,
    *,
    fallback_suffix: str,
    max_identifier_bytes: int,
) -> str:
    """Normalize a protected label into a valid multiword PostgreSQL identifier."""
    ordered_tokens = ordered_semantic_tokens(source_name)
    compact_key = "".join(ordered_tokens)
    alias = _HEADER_ALIASES.get(compact_key)
    if alias is not None:
        candidate = alias
    else:
        candidate = "_".join(ordered_tokens)
        if not candidate:
            candidate = f"source_{fallback_suffix}"
    if not candidate[0].isalpha():
        candidate = f"source_{candidate}"
    if candidate in _POSTGRESQL_RESERVED_NAMES:
        candidate = f"{candidate}_{fallback_suffix}"
    if "_" not in candidate:
        candidate = f"{candidate}_{fallback_suffix}"
    return truncate_identifier(candidate, max_identifier_bytes, source_name)


def unique_column_name(
    candidate: str,
    header_digest: str,
    used_names: set[str],
    max_identifier_bytes: int,
) -> str:
    """Resolve normalized-name collisions without exposing an ordinal identifier."""
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate
    attempt = 1
    while True:
        collision_digest = sha256_text(f"{header_digest}:{attempt}")[:10]
        suffix = "_" + collision_digest
        base_budget = max_identifier_bytes - len(suffix)
        base = candidate.encode("utf-8")[:base_budget]
        fallback = "column"[:base_budget] or "c"
        decoded = base.decode("utf-8", errors="ignore").rstrip("_") or fallback
        resolved = decoded + suffix
        if resolved not in used_names:
            used_names.add(resolved)
            return resolved
        attempt += 1
