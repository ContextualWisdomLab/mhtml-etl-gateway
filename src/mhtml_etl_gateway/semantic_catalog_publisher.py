"""Value-free publication receipts for caller-owned catalog transports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from mhtml_etl_gateway.semantic_catalog_connector import EDGE_ENDPOINT, NODE_ENDPOINT
from mhtml_etl_gateway.semantic_catalog_handoff import (
    CatalogSubmissionEnvelope,
    CatalogWriteRequest,
)

PUBLISHER_CONTRACT_VERSION = "1.0.0"
_OPAQUE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
_DEFAULT_MAX_REQUESTS = 4096


class CatalogPublisherError(ValueError):
    """Safe publication failure that never includes request bodies or secrets."""

    def __init__(
        self,
        code: str,
        *,
        request_index: int | None = None,
        accepted_request_count: int = 0,
    ) -> None:
        """Create a stable error with only bounded reconciliation metadata."""
        self.code = code
        self.request_index = request_index
        self.accepted_request_count = accepted_request_count
        super().__init__(f"catalog_publisher_{code}")

    def to_dict(self) -> dict[str, int | str | None]:
        """Return a privacy-safe machine-readable publication failure."""
        return {
            "error_code": f"catalog_publisher_{self.code}",
            "request_index": self.request_index,
            "accepted_request_count": self.accepted_request_count,
        }


@dataclass(frozen=True, slots=True)
class CatalogPublisherEvidence:
    """Caller-owned proof that governance checks happened before publication."""

    actor_authenticated: bool
    tenant_authorized: bool
    approval_verified: bool
    immutable_audit_reference: str

    def validate(self) -> None:
        """Reject publication unless every required control and audit reference exists."""
        if self.actor_authenticated is not True:
            raise CatalogPublisherError("actor_authentication_required")
        if self.tenant_authorized is not True:
            raise CatalogPublisherError("tenant_authorization_required")
        if self.approval_verified is not True:
            raise CatalogPublisherError("approval_verification_required")
        if (
            not isinstance(self.immutable_audit_reference, str)
            or _OPAQUE_REFERENCE.fullmatch(self.immutable_audit_reference) is None
        ):
            raise CatalogPublisherError("immutable_audit_reference_required")

    def to_dict(self) -> dict[str, bool | str]:
        """Return control evidence without including source values or credentials."""
        return {
            "actor_authenticated": self.actor_authenticated,
            "tenant_authorized": self.tenant_authorized,
            "approval_verified": self.approval_verified,
            "immutable_audit_reference": self.immutable_audit_reference,
        }


@dataclass(frozen=True, slots=True)
class CatalogTransportResponse:
    """Minimal remote response required to prove acceptance of one request."""

    status_code: int
    remote_request_id: str
    accepted: bool

    def validate(self) -> None:
        """Require an HTTP-success response, explicit acceptance, and remote evidence."""
        if type(self.status_code) is not int or not 200 <= self.status_code <= 299:
            raise CatalogPublisherError("remote_status_not_success")
        if self.accepted is not True:
            raise CatalogPublisherError("remote_acceptance_required")
        if (
            not isinstance(self.remote_request_id, str)
            or _OPAQUE_REFERENCE.fullmatch(self.remote_request_id) is None
        ):
            raise CatalogPublisherError("remote_request_id_required")


class CatalogTransport(Protocol):
    """Caller-owned transport that supplies authentication and network policy."""

    def send(self, request: CatalogWriteRequest) -> CatalogTransportResponse:
        """Send one already-planned request and return bounded remote evidence."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class CatalogRequestReceipt:
    """Value-free evidence for one accepted remote graph request."""

    request_index: int
    path: str
    idempotency_key: str
    status_code: int
    remote_request_id: str

    def to_dict(self) -> dict[str, int | str]:
        """Return request identity and remote acceptance without the request body."""
        return {
            "request_index": self.request_index,
            "path": self.path,
            "idempotency_key": self.idempotency_key,
            "status_code": self.status_code,
            "remote_request_id": self.remote_request_id,
        }


@dataclass(frozen=True, slots=True)
class CatalogPublicationReceipt:
    """Immutable, value-free evidence for a fully accepted catalog handoff."""

    publisher_contract_version: str
    envelope_id: str
    target_system: str
    immutable_audit_reference: str
    accepted_request_count: int
    request_receipts: tuple[CatalogRequestReceipt, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialize reconciliation evidence without serializing source content."""
        return {
            "publisher_contract_version": self.publisher_contract_version,
            "envelope_id": self.envelope_id,
            "target_system": self.target_system,
            "immutable_audit_reference": self.immutable_audit_reference,
            "privacy_mode": "value_free",
            "accepted_request_count": self.accepted_request_count,
            "requests": [receipt.to_dict() for receipt in self.request_receipts],
        }


def _validate_request(request: CatalogWriteRequest) -> None:
    """Ensure only known graph POST requests cross the caller-owned transport."""
    if request.method != "POST" or request.path not in {NODE_ENDPOINT, EDGE_ENDPOINT}:
        raise CatalogPublisherError("invalid_catalog_request")
    if not isinstance(
        request.idempotency_key, str
    ) or not request.idempotency_key.startswith("semantic_catalog_write_"):
        raise CatalogPublisherError("invalid_idempotency_key")


def publish_catalog_submission(
    envelope: CatalogSubmissionEnvelope,
    transport: CatalogTransport,
    evidence: CatalogPublisherEvidence,
    *,
    max_requests: int = _DEFAULT_MAX_REQUESTS,
) -> CatalogPublicationReceipt:
    """Publish a governed envelope and return remote acceptance evidence.

    The transport remains caller-owned: this function performs no authentication,
    secret lookup, network setup, retries, or persistence.  It sends each request
    once with its deterministic idempotency key.  A partial remote outcome raises
    ``CatalogPublisherError`` with the accepted prefix count so the caller can
    reconcile rather than accidentally replaying an unknown state.
    """
    if not isinstance(envelope, CatalogSubmissionEnvelope):
        raise CatalogPublisherError("invalid_envelope")
    if not callable(getattr(transport, "send", None)):
        raise CatalogPublisherError("transport_required")
    if (
        type(max_requests) is not int
        or max_requests < 1
        or max_requests > _DEFAULT_MAX_REQUESTS
    ):
        raise CatalogPublisherError("invalid_request_limit")
    evidence.validate()
    requests = envelope.requests
    if not requests:
        raise CatalogPublisherError("no_catalog_requests")
    if len(requests) > max_requests:
        raise CatalogPublisherError("request_limit_exceeded")

    receipts: list[CatalogRequestReceipt] = []
    for index, request in enumerate(requests):
        if not isinstance(request, CatalogWriteRequest):
            raise CatalogPublisherError(
                "invalid_catalog_request",
                request_index=index,
                accepted_request_count=len(receipts),
            )
        try:
            _validate_request(request)
            response = transport.send(request)
            if not isinstance(response, CatalogTransportResponse):
                raise CatalogPublisherError("invalid_transport_response")
            response.validate()
        except CatalogPublisherError as error:
            raise CatalogPublisherError(
                error.code,
                request_index=index,
                accepted_request_count=len(receipts),
            ) from None
        except Exception:
            raise CatalogPublisherError(
                "transport_failed",
                request_index=index,
                accepted_request_count=len(receipts),
            ) from None
        receipts.append(
            CatalogRequestReceipt(
                request_index=index,
                path=request.path,
                idempotency_key=request.idempotency_key,
                status_code=response.status_code,
                remote_request_id=response.remote_request_id,
            )
        )

    return CatalogPublicationReceipt(
        publisher_contract_version=PUBLISHER_CONTRACT_VERSION,
        envelope_id=envelope.envelope_id,
        target_system=envelope.target_system,
        immutable_audit_reference=evidence.immutable_audit_reference,
        accepted_request_count=len(receipts),
        request_receipts=tuple(receipts),
    )
