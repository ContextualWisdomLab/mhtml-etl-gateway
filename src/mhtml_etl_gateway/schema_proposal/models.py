"""Immutable input, policy, and value-free schema proposal models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import unicodedata
from collections.abc import Sequence
from typing import Any

from .errors import SchemaProposalError, SchemaProposalErrorCode


@dataclass(frozen=True, slots=True)
class SchemaProposalPolicy:
    """Versioned, bounded policy used to derive conservative proposals."""

    policy_version: str = "default/1"
    max_columns: int = 4096
    max_samples_per_column: int = 1024
    max_header_characters: int = 1024
    max_value_characters: int = 16_384
    max_identifier_bytes: int = 63
    boolean_true_values: tuple[str, ...] = ("true", "yes", "y", "1")
    boolean_false_values: tuple[str, ...] = ("false", "no", "n", "0")
    date_formats: tuple[str, ...] = ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d")

    def __post_init__(self) -> None:
        """Reject mutable collections, invalid limits, and unstable vocabularies."""
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_POLICY)
        integer_fields = (
            "max_columns",
            "max_samples_per_column",
            "max_header_characters",
            "max_value_characters",
            "max_identifier_bytes",
        )
        for field_name in integer_fields:
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise SchemaProposalError(SchemaProposalErrorCode.INVALID_POLICY)
        if self.max_identifier_bytes < 16:
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_POLICY)
        immutable_collections = (
            self.boolean_true_values,
            self.boolean_false_values,
            self.date_formats,
        )
        if any(not isinstance(value, tuple) for value in immutable_collections):
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_POLICY)
        true_values = normalized_vocabulary(self.boolean_true_values)
        false_values = normalized_vocabulary(self.boolean_false_values)
        if not true_values or not false_values or true_values & false_values:
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_POLICY)
        if not self.date_formats or any(
            not isinstance(item, str) or not item for item in self.date_formats
        ):
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_POLICY)

    def fingerprint_payload(self) -> dict[str, Any]:
        """Return the complete non-secret policy payload used in identities."""
        return asdict(self)


@dataclass(frozen=True, slots=True, repr=False)
class ColumnEvidence:
    """Protected header and representative values retained only in memory."""

    header: str
    samples: tuple[object, ...]

    def __post_init__(self) -> None:
        """Require an exact string header and an immutable sample tuple."""
        if not isinstance(self.header, str):
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_COLUMN)
        if not isinstance(self.samples, tuple):
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_COLUMN)

    def __repr__(self) -> str:
        """Return a fixed representation that cannot reflect protected input."""
        return "ColumnEvidence(protected=True)"


@dataclass(frozen=True, slots=True)
class ColumnProposal:
    """Value-free proposal and bounded aggregate evidence for one column."""

    source_header_sha256: str
    evidence_fingerprint_sha256: str
    target_column_name: str
    proposed_postgresql_type: str
    proposed_nullable: bool
    sample_count: int
    blank_count: int
    nonblank_count: int
    distinct_nonblank_count: int
    maximum_value_characters: int
    evidence_codes: tuple[str, ...]
    review_required: bool
    review_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready proposal containing no raw header or value."""
        return {
            "source_header_sha256": self.source_header_sha256,
            "evidence_fingerprint_sha256": self.evidence_fingerprint_sha256,
            "target_column_name": self.target_column_name,
            "proposed_postgresql_type": self.proposed_postgresql_type,
            "proposed_nullable": self.proposed_nullable,
            "sample_count": self.sample_count,
            "blank_count": self.blank_count,
            "nonblank_count": self.nonblank_count,
            "distinct_nonblank_count": self.distinct_nonblank_count,
            "maximum_value_characters": self.maximum_value_characters,
            "evidence_codes": list(self.evidence_codes),
            "review_required": self.review_required,
            "review_reasons": list(self.review_reasons),
        }


@dataclass(frozen=True, slots=True)
class SchemaProposal:
    """Content-addressed, ordered, value-free PostgreSQL schema proposal."""

    algorithm_version: str
    policy_version: str
    source_table_label_sha256: str
    table_fingerprint_sha256: str
    proposal_fingerprint_sha256: str
    target_table_name: str
    column_count: int
    columns: tuple[ColumnProposal, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the stable public proposal artifact without protected input."""
        return {
            "algorithm_version": self.algorithm_version,
            "policy_version": self.policy_version,
            "source_table_label_sha256": self.source_table_label_sha256,
            "table_fingerprint_sha256": self.table_fingerprint_sha256,
            "proposal_fingerprint_sha256": self.proposal_fingerprint_sha256,
            "target_table_name": self.target_table_name,
            "column_count": self.column_count,
            "columns": [column.to_dict() for column in self.columns],
        }


def normalized_vocabulary(values: Sequence[str]) -> frozenset[str]:
    """Normalize one policy vocabulary and reject non-string members."""
    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise SchemaProposalError(SchemaProposalErrorCode.INVALID_POLICY)
        normalized.add(unicodedata.normalize("NFKC", value).casefold().strip())
    return frozenset(normalized)
