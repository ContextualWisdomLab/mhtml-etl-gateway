"""Side-effect-free orchestration for value-free schema proposals."""

from __future__ import annotations

from .errors import SchemaProposalError, SchemaProposalErrorCode
from .identity import bounded_header, canonical_value, is_blank, sha256_text, stable_digest
from .inference import infer_type
from .models import (
    ColumnEvidence,
    ColumnProposal,
    SchemaProposal,
    SchemaProposalPolicy,
)
from .naming import normalized_identifier, unique_column_name

_ALGORITHM_VERSION = "value_free_schema_proposal/1"


def _column_proposal(
    evidence: ColumnEvidence,
    policy: SchemaProposalPolicy,
    used_names: set[str],
) -> ColumnProposal:
    """Build one bounded, value-free column proposal."""
    header = bounded_header(evidence.header, policy)
    if len(evidence.samples) > policy.max_samples_per_column:
        raise SchemaProposalError(SchemaProposalErrorCode.TOO_MANY_SAMPLES)

    canonical = tuple(canonical_value(value, policy) for value in evidence.samples)
    nonblank = tuple(item for item in canonical if not is_blank(*item))
    blank_count = len(canonical) - len(nonblank)
    header_digest = sha256_text(header)
    value_digests = tuple(
        stable_digest({"kind": kind, "value": rendered})
        for kind, rendered in canonical
    )
    evidence_fingerprint = stable_digest(
        {
            "source_header_sha256": header_digest,
            "ordered_value_sha256": value_digests,
        }
    )
    candidate_name = normalized_identifier(
        header,
        fallback_suffix="column",
        max_identifier_bytes=policy.max_identifier_bytes,
    )
    target_name = unique_column_name(
        candidate_name,
        header_digest,
        used_names,
        policy.max_identifier_bytes,
    )
    proposed_type, evidence_codes, review_reasons = infer_type(
        header,
        nonblank,
        policy,
    )
    distinct_count = len(
        {
            stable_digest({"kind": kind, "value": rendered})
            for kind, rendered in nonblank
        }
    )
    maximum_characters = max(
        (len(rendered) for _, rendered in nonblank),
        default=0,
    )
    return ColumnProposal(
        source_header_sha256=header_digest,
        evidence_fingerprint_sha256=evidence_fingerprint,
        target_column_name=target_name,
        proposed_postgresql_type=proposed_type,
        proposed_nullable=True,
        sample_count=len(canonical),
        blank_count=blank_count,
        nonblank_count=len(nonblank),
        distinct_nonblank_count=distinct_count,
        maximum_value_characters=maximum_characters,
        evidence_codes=evidence_codes,
        review_required=bool(review_reasons),
        review_reasons=review_reasons,
    )


def propose_postgresql_schema(
    table_label: str,
    columns: tuple[ColumnEvidence, ...],
    *,
    policy: SchemaProposalPolicy | None = None,
) -> SchemaProposal:
    """Create a deterministic proposal without serializing protected input."""
    effective_policy = policy or SchemaProposalPolicy()
    if not isinstance(table_label, str) or not table_label.strip():
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_TABLE_LABEL)
    if len(table_label) > effective_policy.max_header_characters:
        raise SchemaProposalError(SchemaProposalErrorCode.VALUE_TOO_LARGE)
    if not isinstance(columns, tuple):
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_COLUMN)
    if len(columns) > effective_policy.max_columns:
        raise SchemaProposalError(SchemaProposalErrorCode.TOO_MANY_COLUMNS)
    if not columns or any(
        not isinstance(column, ColumnEvidence) for column in columns
    ):
        raise SchemaProposalError(SchemaProposalErrorCode.INVALID_COLUMN)

    target_table_name = normalized_identifier(
        table_label,
        fallback_suffix="record",
        max_identifier_bytes=effective_policy.max_identifier_bytes,
    )
    table_label_digest = sha256_text(table_label)
    used_names: set[str] = set()
    proposals = tuple(
        _column_proposal(column, effective_policy, used_names)
        for column in columns
    )
    table_fingerprint = stable_digest(
        {
            "source_table_label_sha256": table_label_digest,
            "ordered_source_header_sha256": tuple(
                proposal.source_header_sha256 for proposal in proposals
            ),
        }
    )
    proposal_payload = {
        "algorithm_version": _ALGORITHM_VERSION,
        "policy": effective_policy.fingerprint_payload(),
        "source_table_label_sha256": table_label_digest,
        "table_fingerprint_sha256": table_fingerprint,
        "target_table_name": target_table_name,
        "columns": tuple(proposal.to_dict() for proposal in proposals),
    }
    return SchemaProposal(
        algorithm_version=_ALGORITHM_VERSION,
        policy_version=effective_policy.policy_version,
        source_table_label_sha256=table_label_digest,
        table_fingerprint_sha256=table_fingerprint,
        proposal_fingerprint_sha256=stable_digest(proposal_payload),
        target_table_name=target_table_name,
        column_count=len(proposals),
        columns=proposals,
    )
