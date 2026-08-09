"""Conservative PostgreSQL type inference from bounded protected evidence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import re
import unicodedata

from .models import SchemaProposalPolicy, normalized_vocabulary
from .naming import (
    has_boolean_semantics,
    has_date_semantics,
    has_identifier_semantics,
)

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_NUMERIC_PATTERN = re.compile(
    r"^[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?$"
)


def integer_text(rendered: str) -> int | None:
    """Parse exact integer syntax without coercing decimals or whitespace."""
    stripped = rendered.strip()
    if not _INTEGER_PATTERN.fullmatch(stripped):
        return None
    return int(stripped)


def numeric_decimal(kind: str, rendered: str) -> Decimal | None:
    """Parse exact numeric evidence while retaining binary-float provenance."""
    stripped = rendered.strip()
    if kind in {"integer", "decimal"}:
        return Decimal(stripped)
    if kind == "float":
        return Decimal.from_float(float.fromhex(stripped))
    if kind == "string" and _NUMERIC_PATTERN.fullmatch(stripped):
        value = Decimal(stripped)
        return value if value.is_finite() else None
    return None


def parse_supported_date(
    kind: str,
    rendered: str,
    policy: SchemaProposalPolicy,
) -> bool:
    """Return whether one value is a lossless supported date without time data."""
    if kind == "date":
        return True
    if kind != "string":
        return False
    candidate = rendered.strip()
    for date_format in policy.date_formats:
        try:
            datetime.strptime(candidate, date_format)
        except ValueError:
            continue
        return True
    return False


def boolean_value(
    kind: str,
    rendered: str,
    policy: SchemaProposalPolicy,
) -> bool | None:
    """Return a boolean only for native bool or approved exact vocabulary."""
    if kind == "boolean":
        return rendered == "true"
    if kind != "string":
        return None
    candidate = unicodedata.normalize("NFKC", rendered).casefold().strip()
    true_values = normalized_vocabulary(policy.boolean_true_values)
    false_values = normalized_vocabulary(policy.boolean_false_values)
    if candidate in true_values:
        return True
    if candidate in false_values:
        return False
    return None


def infer_type(
    header: str,
    nonblank: tuple[tuple[str, str], ...],
    policy: SchemaProposalPolicy,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Return conservative type, evidence codes, and explicit review reasons."""
    if not nonblank:
        return "text", ("no_nonblank_evidence",), ("no_nonblank_evidence",)

    kinds = {kind for kind, _ in nonblank}
    identifier_semantics = has_identifier_semantics(header)
    date_semantics = has_date_semantics(header)
    boolean_semantics = has_boolean_semantics(header)
    stripped_strings = tuple(
        rendered.strip() for kind, rendered in nonblank if kind == "string"
    )
    leading_zero = any(
        re.fullmatch(r"[+-]?0\d+", item) is not None for item in stripped_strings
    )

    if identifier_semantics or leading_zero:
        evidence = ["identifier_semantics"] if identifier_semantics else []
        if leading_zero:
            evidence.append("leading_zero_value")
        return "text", tuple(evidence), ()

    boolean_values = tuple(
        boolean_value(kind, rendered, policy) for kind, rendered in nonblank
    )
    if all(value is not None for value in boolean_values):
        if kinds == {"boolean"} or boolean_semantics:
            return "boolean", ("exact_boolean_vocabulary",), ()

    if date_semantics:
        if all(
            parse_supported_date(kind, rendered, policy)
            for kind, rendered in nonblank
        ):
            return "date", ("header_date_semantics", "all_values_valid_dates"), ()
        return (
            "text",
            ("header_date_semantics", "invalid_date_evidence"),
            ("date_semantics_with_invalid_value",),
        )

    integer_values = tuple(integer_text(rendered) for _, rendered in nonblank)
    if kinds <= {"integer", "string"} and all(
        value is not None for value in integer_values
    ):
        values = tuple(value for value in integer_values if value is not None)
        if all(-(2**63) <= value <= (2**63 - 1) for value in values):
            return "bigint", ("all_values_exact_int64",), ()
        return (
            "numeric",
            ("all_values_exact_integers", "outside_int64_range"),
            ("integer_outside_int64_range",),
        )

    numeric_values = tuple(
        numeric_decimal(kind, rendered) for kind, rendered in nonblank
    )
    if all(value is not None for value in numeric_values):
        evidence = ["all_values_exact_numeric"]
        review: list[str] = []
        if "float" in kinds:
            evidence.append("binary_float_evidence")
            review.append("binary_float_requires_review")
        return "numeric", tuple(evidence), tuple(review)

    if kinds == {"string"}:
        return "text", ("all_values_text",), ()
    return (
        "text",
        ("mixed_or_unrecognized_values",),
        ("mixed_or_unrecognized_values",),
    )
