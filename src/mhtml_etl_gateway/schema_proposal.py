"""Deterministic, value-free PostgreSQL schema proposal contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import date
from enum import Enum
import hashlib
import json
import re
from typing import Any
import unicodedata


_MAX_POSTGRES_IDENTIFIER_BYTES = 63
_SCHEMA_PROPOSAL_PREFIX = "schema_proposal_"
_SOURCE_HASH = re.compile(r"^[0-9a-fA-F]{64}$")
_INTEGER_VALUE = re.compile(r"^[+-]?[0-9]+$")
_DECIMAL_VALUE = re.compile(r"^[+-]?[0-9]+\.[0-9]+$")
_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_COMPACT_DATE = re.compile(r"^[0-9]{8}$")
_CAMEL_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
_UNDERSCORE_RUN = re.compile(r"_+")

_HEADER_ALIASES = {
    "MANDT": "client_code",
    "GUID": "global_identifier",
    "DOCNOSUB": "document_subnumber",
    "DUEDT": "due_date",
    "KUNNR": "customer_number",
}
_RESERVED_WORDS = {
    "all",
    "analyse",
    "analyze",
    "and",
    "any",
    "array",
    "as",
    "asc",
    "asymmetric",
    "authorization",
    "binary",
    "both",
    "case",
    "cast",
    "check",
    "collate",
    "column",
    "constraint",
    "create",
    "current_date",
    "current_role",
    "current_time",
    "current_timestamp",
    "current_user",
    "default",
    "deferrable",
    "desc",
    "distinct",
    "do",
    "else",
    "end",
    "except",
    "false",
    "for",
    "foreign",
    "from",
    "grant",
    "group",
    "having",
    "in",
    "initially",
    "intersect",
    "into",
    "lateral",
    "leading",
    "limit",
    "localtime",
    "localtimestamp",
    "new",
    "not",
    "null",
    "off",
    "offset",
    "old",
    "on",
    "only",
    "or",
    "order",
    "placing",
    "primary",
    "references",
    "returning",
    "select",
    "session_user",
    "some",
    "symmetric",
    "table",
    "then",
    "to",
    "trailing",
    "true",
    "union",
    "unique",
    "user",
    "using",
    "variadic",
    "when",
    "where",
    "window",
    "with",
}
_IDENTIFIER_TOKENS = {
    "account",
    "client",
    "code",
    "customer",
    "document",
    "guid",
    "id",
    "identifier",
    "no",
    "number",
    "subnumber",
}
_DATE_TOKENS = {
    "created",
    "date",
    "dt",
    "due",
    "end",
    "modified",
    "start",
    "updated",
}
_BOOLEAN_VALUES = {"true", "false"}
_SIGNED_BIGINT_MIN = -(2**63)
_SIGNED_BIGINT_MAX = 2**63 - 1


class PostgresType(str, Enum):
    """Conservative PostgreSQL types emitted by the proposal engine."""

    TEXT = "text"
    BOOLEAN = "boolean"
    DATE = "date"
    BIGINT = "bigint"
    NUMERIC = "numeric"


class SchemaProposalErrorCode(str, Enum):
    """Stable machine-readable failures for protected proposal inputs."""

    INVALID_SOURCE_HASH = "invalid_source_hash"
    INVALID_INPUT = "invalid_input"
    TOO_MANY_COLUMNS = "too_many_columns"
    HEADER_TOO_LARGE = "header_too_large"
    TOO_MANY_SAMPLES = "too_many_samples"
    SAMPLE_VALUE_TOO_LARGE = "sample_value_too_large"


_ERROR_MESSAGES = {
    SchemaProposalErrorCode.INVALID_SOURCE_HASH: (
        "Source hash must be a SHA-256 value"
    ),
    SchemaProposalErrorCode.INVALID_INPUT: "Schema proposal input is invalid",
    SchemaProposalErrorCode.TOO_MANY_COLUMNS: (
        "Schema proposal exceeds the column limit"
    ),
    SchemaProposalErrorCode.HEADER_TOO_LARGE: (
        "A protected header exceeds the configured limit"
    ),
    SchemaProposalErrorCode.TOO_MANY_SAMPLES: (
        "A protected column exceeds the sample limit"
    ),
    SchemaProposalErrorCode.SAMPLE_VALUE_TOO_LARGE: (
        "A protected sample value exceeds the configured limit"
    ),
}


class SchemaProposalError(Exception):
    """Fail-closed error with fixed text that never reflects protected values."""

    def __init__(self, code: SchemaProposalErrorCode) -> None:
        """Initialize the error from its stable code and approved message."""
        self.code = code
        self.message = _ERROR_MESSAGES[code]
        super().__init__(f"{code.value}: {self.message}")

    def to_dict(self) -> dict[str, str]:
        """Return the value-free public error representation."""
        return {"error_code": self.code.value, "message": self.message}


@dataclass(frozen=True, slots=True)
class SchemaProposalPolicy:
    """Versioned resource and algorithm policy for protected schema evidence."""

    algorithm_version: str = "1.0.0"
    max_columns: int = 4096
    max_header_chars: int = 4096
    max_samples_per_column: int = 10_000
    max_value_chars: int = 1_000_000

    def __post_init__(self) -> None:
        """Reject ambiguous versions and non-positive or boolean budgets."""
        if (
            not isinstance(self.algorithm_version, str)
            or not self.algorithm_version.strip()
        ):
            raise ValueError("algorithm_version must be a non-empty string")
        for field_definition in fields(self):
            if field_definition.name == "algorithm_version":
                continue
            value = getattr(self, field_definition.name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"{field_definition.name} must be a positive integer"
                )


@dataclass(frozen=True, slots=True)
class ProtectedColumnInput:
    """Caller-held header and bounded values that never enter proposal output."""

    header: str
    values: tuple[str | None, ...]
    complete: bool = False

    def __post_init__(self) -> None:
        """Require exact immutable container types before protected processing."""
        if not isinstance(self.header, str):
            raise ValueError("header must be a string")
        if not isinstance(self.values, tuple):
            raise ValueError("values must be a tuple")
        if not isinstance(self.complete, bool):
            raise ValueError("complete must be a boolean")


@dataclass(frozen=True, slots=True)
class ColumnProposal:
    """Value-free mapping and aggregate evidence for one protected column."""

    source_header_hash_sha256: str
    target_column_name: str
    proposed_type: PostgresType
    nullable: bool
    non_null_count: int
    distinct_count: int
    maximum_text_length: int
    maximum_numeric_precision: int | None
    maximum_numeric_scale: int | None
    review_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return hashes, derived decisions, and aggregate evidence only."""
        return {
            "source_header_hash_sha256": self.source_header_hash_sha256,
            "target_column_name": self.target_column_name,
            "proposed_type": self.proposed_type.value,
            "nullable": self.nullable,
            "non_null_count": self.non_null_count,
            "distinct_count": self.distinct_count,
            "maximum_text_length": self.maximum_text_length,
            "maximum_numeric_precision": self.maximum_numeric_precision,
            "maximum_numeric_scale": self.maximum_numeric_scale,
            "review_reasons": list(self.review_reasons),
        }


@dataclass(frozen=True, slots=True)
class SchemaProposal:
    """Content-addressed ordered schema proposal with no raw protected values."""

    schema_proposal_id: str
    proposal_version: str
    source_hash_sha256: str
    table_fingerprint_sha256: str
    columns: tuple[ColumnProposal, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the stable value-free proposal representation."""
        return {
            "schema_proposal_id": self.schema_proposal_id,
            "proposal_version": self.proposal_version,
            "source_hash_sha256": self.source_hash_sha256,
            "table_fingerprint_sha256": self.table_fingerprint_sha256,
            "columns": [column.to_dict() for column in self.columns],
        }


def _sha256_text(value: str) -> str:
    """Hash exact protected text without normalizing its evidence identity."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _truncate_utf8(value: str, maximum_bytes: int) -> str:
    """Return the longest valid UTF-8 prefix within the byte budget."""
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return value
    shortened = encoded[:maximum_bytes]
    while shortened and (shortened[-1] & 0b11000000) == 0b10000000:
        shortened = shortened[:-1]
    while shortened:
        try:
            return shortened.decode("utf-8")
        except UnicodeDecodeError:
            shortened = shortened[:-1]
    return ""


def _fit_identifier(value: str) -> str:
    """Fit a multiword identifier into PostgreSQL's UTF-8 byte limit."""
    if len(value.encode("utf-8")) <= _MAX_POSTGRES_IDENTIFIER_BYTES:
        return value
    prefix, _, final_token = value.rpartition("_")
    suffix = f"_{final_token}"
    if len(suffix.encode("utf-8")) >= _MAX_POSTGRES_IDENTIFIER_BYTES:
        return _truncate_utf8(
            f"source_{final_token}",
            _MAX_POSTGRES_IDENTIFIER_BYTES,
        ).rstrip("_")
    maximum_prefix = _MAX_POSTGRES_IDENTIFIER_BYTES - len(
        suffix.encode("utf-8")
    )
    fitted_prefix = _truncate_utf8(prefix, maximum_prefix).rstrip("_")
    if not fitted_prefix:
        fitted_prefix = _truncate_utf8("source", maximum_prefix)
    return f"{fitted_prefix}{suffix}"


def _canonical_name(header: str) -> str:
    """Derive a multiword snake_case name without altering source evidence."""
    compatibility = unicodedata.normalize("NFKC", header).strip()
    alias = _HEADER_ALIASES.get(compatibility.upper())
    if alias is not None:
        return alias

    separated = _CAMEL_ACRONYM.sub(r"\1_\2", compatibility)
    separated = _CAMEL_BOUNDARY.sub(r"\1_\2", separated)
    normalized = _NON_WORD.sub("_", separated).lower()
    normalized = _UNDERSCORE_RUN.sub("_", normalized).strip("_")

    if not normalized or not any(character.isalnum() for character in normalized):
        return f"source_field_{_sha256_text(header)[:8]}"
    if normalized[0].isdigit():
        normalized = f"source_{normalized}"
    if normalized in _RESERVED_WORDS or "_" not in normalized:
        normalized = f"{normalized}_field"
    return _fit_identifier(normalized)


def _collision_name(base: str, header: str, position: int) -> str:
    """Add an opaque deterministic suffix without exposing a sequence number."""
    digest = _sha256_text(f"{header}\0{position}")[:8]
    suffix = f"_{digest}"
    maximum_base = _MAX_POSTGRES_IDENTIFIER_BYTES - len(suffix)
    fitted_base = _truncate_utf8(base, maximum_base).rstrip("_")
    return f"{fitted_base}{suffix}"


def _tokens(name: str) -> set[str]:
    """Return normalized identifier tokens used only for conservative hints."""
    return set(name.split("_"))


def _is_valid_date(value: str) -> bool:
    """Validate supported ISO or compact Gregorian calendar dates."""
    try:
        if _ISO_DATE.fullmatch(value):
            date.fromisoformat(value)
            return True
        if _COMPACT_DATE.fullmatch(value):
            date(int(value[:4]), int(value[4:6]), int(value[6:8]))
            return True
    except ValueError:
        return False
    return False


def _has_leading_zero(value: str) -> bool:
    """Detect signed integral portions whose textual width carries identity."""
    unsigned = value.removeprefix("+").removeprefix("-")
    integer_portion = unsigned.split(".", 1)[0]
    return len(integer_portion) > 1 and integer_portion.startswith("0")


def _numeric_dimensions(value: str) -> tuple[int, int]:
    """Return decimal precision and scale without numeric conversion."""
    unsigned = value.removeprefix("+").removeprefix("-")
    integer_portion, separator, fractional = unsigned.partition(".")
    scale = len(fractional) if separator else 0
    return len(integer_portion) + scale, scale


def _infer_type(
    target_name: str,
    values: tuple[str, ...],
) -> tuple[PostgresType, tuple[str, ...], int | None, int | None]:
    """Infer one conservative type and value-free review evidence."""
    if not values:
        return PostgresType.TEXT, ("empty_column",), None, None

    name_tokens = _tokens(target_name)
    identifier_semantics = bool(name_tokens & _IDENTIFIER_TOKENS)
    date_semantics = bool(name_tokens & _DATE_TOKENS)
    lowered = {value.lower() for value in values}
    if lowered <= _BOOLEAN_VALUES:
        if identifier_semantics:
            return PostgresType.TEXT, ("identifier_semantics",), None, None
        return PostgresType.BOOLEAN, (), None, None

    all_valid_dates = all(_is_valid_date(value) for value in values)
    leading_zero = any(_has_leading_zero(value) for value in values)

    if all_valid_dates:
        if date_semantics and not identifier_semantics:
            return PostgresType.DATE, (), None, None
        reasons = []
        if identifier_semantics:
            reasons.append("identifier_semantics")
        reasons.append("date_semantics_missing")
        return PostgresType.TEXT, tuple(reasons), None, None

    if all(_INTEGER_VALUE.fullmatch(value) for value in values):
        if leading_zero or identifier_semantics:
            reasons = []
            if identifier_semantics:
                reasons.append("identifier_semantics")
            if leading_zero:
                reasons.append("leading_zero_identifier")
            return PostgresType.TEXT, tuple(reasons), None, None
        integers = tuple(int(value) for value in values)
        precision = max(_numeric_dimensions(value)[0] for value in values)
        if all(
            _SIGNED_BIGINT_MIN <= value <= _SIGNED_BIGINT_MAX
            for value in integers
        ):
            return PostgresType.BIGINT, (), precision, 0
        return (
            PostgresType.NUMERIC,
            ("bigint_range_exceeded",),
            precision,
            0,
        )

    if all(_DECIMAL_VALUE.fullmatch(value) for value in values):
        if leading_zero or identifier_semantics:
            reasons = []
            if identifier_semantics:
                reasons.append("identifier_semantics")
            if leading_zero:
                reasons.append("leading_zero_identifier")
            return PostgresType.TEXT, tuple(reasons), None, None
        dimensions = tuple(_numeric_dimensions(value) for value in values)
        return (
            PostgresType.NUMERIC,
            (),
            max(precision for precision, _ in dimensions),
            max(scale for _, scale in dimensions),
        )

    reasons = ["mixed_or_unrecognized_values"]
    if identifier_semantics:
        reasons.insert(0, "identifier_semantics")
    return PostgresType.TEXT, tuple(reasons), None, None


def _validate_column(
    column: ProtectedColumnInput,
    policy: SchemaProposalPolicy,
) -> None:
    """Validate bounded protected input without reflecting any value."""
    if len(column.header) > policy.max_header_chars:
        raise SchemaProposalError(SchemaProposalErrorCode.HEADER_TOO_LARGE)
    if len(column.values) > policy.max_samples_per_column:
        raise SchemaProposalError(SchemaProposalErrorCode.TOO_MANY_SAMPLES)
    for value in column.values:
        if value is not None and not isinstance(value, str):
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_INPUT)
        if isinstance(value, str) and len(value) > policy.max_value_chars:
            raise SchemaProposalError(
                SchemaProposalErrorCode.SAMPLE_VALUE_TOO_LARGE
            )


def _column_proposal(
    column: ProtectedColumnInput,
    target_name: str,
) -> ColumnProposal:
    """Create value-free aggregate evidence for one validated protected column."""
    stripped_values = tuple(
        value.strip()
        for value in column.values
        if value is not None and value.strip()
    )
    null_count = len(column.values) - len(stripped_values)
    proposed_type, type_reasons, precision, scale = _infer_type(
        target_name,
        stripped_values,
    )
    reasons = list(type_reasons)
    if not column.complete:
        reasons.insert(0, "sample_only_nullability")
    return ColumnProposal(
        source_header_hash_sha256=_sha256_text(column.header),
        target_column_name=target_name,
        proposed_type=proposed_type,
        nullable=not column.complete or null_count > 0 or not stripped_values,
        non_null_count=len(stripped_values),
        distinct_count=len(set(stripped_values)),
        maximum_text_length=max(
            (len(value) for value in stripped_values),
            default=0,
        ),
        maximum_numeric_precision=precision,
        maximum_numeric_scale=scale,
        review_reasons=tuple(reasons),
    )


def _canonical_json(value: Any) -> bytes:
    """Serialize proposal identity inputs deterministically as UTF-8 JSON."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def propose_schema(
    source_hash_sha256: str,
    columns: Sequence[ProtectedColumnInput],
    *,
    policy: SchemaProposalPolicy | None = None,
) -> SchemaProposal:
    """Produce a deterministic value-free proposal from protected in-process data."""
    effective_policy = policy or SchemaProposalPolicy()
    if not isinstance(source_hash_sha256, str) or not _SOURCE_HASH.fullmatch(
        source_hash_sha256
    ):
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_SOURCE_HASH)
    if isinstance(columns, (str, bytes)) or not isinstance(columns, Sequence):
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_INPUT)
    if not columns:
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_INPUT)
    if len(columns) > effective_policy.max_columns:
        raise SchemaProposalError(SchemaProposalErrorCode.TOO_MANY_COLUMNS)
    if any(not isinstance(column, ProtectedColumnInput) for column in columns):
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_INPUT)

    normalized_source_hash = source_hash_sha256.lower()
    used_names: set[str] = set()
    column_proposals: list[ColumnProposal] = []
    header_hashes: list[str] = []
    for position, column in enumerate(columns):
        _validate_column(column, effective_policy)
        base_name = _canonical_name(column.header)
        target_name = (
            base_name
            if base_name not in used_names
            else _collision_name(base_name, column.header, position)
        )
        if target_name in used_names:
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_INPUT)
        used_names.add(target_name)
        proposal = _column_proposal(column, target_name)
        column_proposals.append(proposal)
        header_hashes.append(proposal.source_header_hash_sha256)

    table_fingerprint = hashlib.sha256(
        _canonical_json(header_hashes)
    ).hexdigest()
    identity_payload = {
        "proposal_version": effective_policy.algorithm_version.strip(),
        "source_hash_sha256": normalized_source_hash,
        "table_fingerprint_sha256": table_fingerprint,
        "columns": [proposal.to_dict() for proposal in column_proposals],
    }
    proposal_digest = hashlib.sha256(_canonical_json(identity_payload)).hexdigest()
    return SchemaProposal(
        schema_proposal_id=f"{_SCHEMA_PROPOSAL_PREFIX}{proposal_digest[:32]}",
        proposal_version=effective_policy.algorithm_version.strip(),
        source_hash_sha256=normalized_source_hash,
        table_fingerprint_sha256=table_fingerprint,
        columns=tuple(column_proposals),
    )
