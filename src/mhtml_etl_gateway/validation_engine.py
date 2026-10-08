"""Fail-closed validation before PostgreSQL load."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

# Default required headers for ZCRHT811-shaped SAP ALV CRM exports.
DEFAULT_REQUIRED_HEADERS: tuple[str, ...] = ("MANDT", "GUID")

# Weaker signals that still indicate ZCRHT811-family CRM exports even when
# MANDT/GUID are missing (so we can fail closed on missing required headers).
_ZCRHT_HINT_HEADERS = frozenset(
    {
        "DOCNOSUB",
        "ACTHGUID",
        "VOCTP",
        "VOCCTS",
        "ERTCD",
        "ZGBISPJTNO",
    }
)


class ValidationError(ValueError):
    """Fail-closed validation failure — do not load business rows."""


@dataclass(frozen=True)
class ValidationResult:
    """Successful fail-closed validation outcome for one extracted table."""

    ok: bool
    headers: list[str]
    row_count: int
    required_headers: tuple[str, ...]
    messages: tuple[str, ...] = ()


def is_zcrht811_shaped(
    headers: Sequence[str], *, table_name: str | None = None
) -> bool:
    """Heuristic for ZCRHT811-family exports — independent of required-header check.

    True when table name suggests ZCRHT811, or headers include MANDT/GUID, or
    enough ZCRHT-specific column names appear (so missing MANDT/GUID still
    triggers required-header failure rather than silently skipping validation).
    """
    if table_name and "zcrht811" in table_name.lower():
        return True
    upper = {h.upper() for h in headers}
    if "MANDT" in upper or "GUID" in upper:
        return True
    hints = upper & _ZCRHT_HINT_HEADERS
    if len(hints) >= 2:
        return True
    return False


def resolve_required_headers(
    headers: Sequence[str],
    *,
    table_name: str | None = None,
    required_headers: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Return required header names for this extract.

    If ``required_headers`` is explicitly provided (including empty), use it.
    Otherwise enforce DEFAULT_REQUIRED_HEADERS when the table is ZCRHT811-shaped.
    """
    if required_headers is not None:
        return tuple(required_headers)
    if is_zcrht811_shaped(headers, table_name=table_name):
        return DEFAULT_REQUIRED_HEADERS
    return ()


def validate_extracted_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    table_name: str | None = None,
    required_headers: Sequence[str] | None = None,
    require_data_rows: bool = True,
    allow_ragged: bool = False,
) -> ValidationResult:
    """Validate headers/rows before load. Raises ValidationError on failure."""
    msgs: list[str] = []
    hdrs = [str(h).strip() for h in headers]

    if not hdrs or not any(hdrs):
        raise ValidationError("validation failed: no headers")

    if any(not h for h in hdrs):
        msgs.append("blank header name(s) present")

    req = resolve_required_headers(
        hdrs, table_name=table_name, required_headers=required_headers
    )
    # Case-insensitive required-header check (SAP exports vary casing).
    present_upper = {h.upper() for h in hdrs}
    missing = [h for h in req if h.upper() not in present_upper]
    if missing:
        raise ValidationError(
            f"validation failed: missing required headers {missing}; present={hdrs[:20]}"
        )

    width = len(hdrs)
    if not allow_ragged:
        for i, row in enumerate(rows):
            if len(row) != width:
                raise ValidationError(
                    f"validation failed: row {i + 1} has {len(row)} cells, expected {width}"
                )

    if require_data_rows and len(rows) < 1:
        raise ValidationError("validation failed: no data rows")

    return ValidationResult(
        ok=True,
        headers=list(hdrs),
        row_count=len(rows),
        required_headers=req,
        messages=tuple(msgs),
    )
