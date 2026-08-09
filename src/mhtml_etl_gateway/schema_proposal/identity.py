"""Canonical protected-value identity and bounded evidence helpers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import math
import unicodedata
from typing import Any

from .errors import SchemaProposalError, SchemaProposalErrorCode
from .models import SchemaProposalPolicy


def sha256_text(value: str) -> str:
    """Return a lowercase SHA-256 digest for an exact UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_digest(payload: Any) -> str:
    """Hash a canonical JSON representation used by proposal identities."""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def bounded_header(header: str, policy: SchemaProposalPolicy) -> str:
    """Validate a protected header without normalizing its identity bytes."""
    if not header.strip():
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_COLUMN)
    if len(header) > policy.max_header_characters:
        raise SchemaProposalError(SchemaProposalErrorCode.VALUE_TOO_LARGE)
    return header


def decimal_fixed_character_count(value: Decimal) -> int:
    """Return fixed-point output length without allocating exponent-sized text."""
    if not value.is_finite():
        raise SchemaProposalError(SchemaProposalErrorCode.UNSUPPORTED_VALUE)
    sign, raw_digits, raw_exponent = value.as_tuple()
    digits = list(raw_digits)
    exponent = raw_exponent
    if not any(digits):
        return 1
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    digit_count = len(digits)
    sign_count = 1 if sign else 0
    if exponent >= 0:
        return sign_count + digit_count + exponent
    integer_digits = digit_count + exponent
    if integer_digits > 0:
        return sign_count + digit_count + 1
    return sign_count + 2 + (-integer_digits) + digit_count


def canonical_decimal(value: Decimal) -> str:
    """Return an exact finite decimal representation without exponent drift."""
    if not value.is_finite():
        raise SchemaProposalError(SchemaProposalErrorCode.UNSUPPORTED_VALUE)
    rendered = format(value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return "0" if rendered in {"-0", ""} else rendered


def canonical_value(
    value: object,
    policy: SchemaProposalPolicy,
) -> tuple[str, str]:
    """Return a typed canonical value for hashes and aggregate evidence."""
    if value is None:
        return "null", ""
    if isinstance(value, bool):
        return "boolean", "true" if value else "false"
    if isinstance(value, int):
        if value.bit_length() > policy.max_value_characters * 4:
            raise SchemaProposalError(SchemaProposalErrorCode.VALUE_TOO_LARGE)
        rendered = str(value)
        if len(rendered) > policy.max_value_characters:
            raise SchemaProposalError(SchemaProposalErrorCode.VALUE_TOO_LARGE)
        return "integer", rendered
    if isinstance(value, Decimal):
        if decimal_fixed_character_count(value) > policy.max_value_characters:
            raise SchemaProposalError(SchemaProposalErrorCode.VALUE_TOO_LARGE)
        rendered = canonical_decimal(value)
        if len(rendered) > policy.max_value_characters:
            raise SchemaProposalError(SchemaProposalErrorCode.VALUE_TOO_LARGE)
        return "decimal", rendered
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SchemaProposalError(SchemaProposalErrorCode.UNSUPPORTED_VALUE)
        return "float", value.hex()
    if isinstance(value, datetime):
        return "datetime", value.isoformat(timespec="microseconds")
    if isinstance(value, date):
        return "date", value.isoformat()
    if isinstance(value, str):
        rendered = unicodedata.normalize("NFC", value)
        if len(rendered) > policy.max_value_characters:
            raise SchemaProposalError(SchemaProposalErrorCode.VALUE_TOO_LARGE)
        return "string", rendered
    raise SchemaProposalError(SchemaProposalErrorCode.UNSUPPORTED_VALUE)


def is_blank(kind: str, rendered: str) -> bool:
    """Return whether a canonical value supplies no type evidence."""
    return kind == "null" or (kind == "string" and not rendered.strip())
