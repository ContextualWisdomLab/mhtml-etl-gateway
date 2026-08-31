from __future__ import annotations

from dataclasses import replace

import pytest

from mhtml_etl_gateway.schema_proposal import ProtectedColumnInput, propose_schema
from mhtml_etl_gateway.semantic_catalog_connector import build_semantic_catalog_manifest
from mhtml_etl_gateway.semantic_catalog_handoff import (
    CatalogWriteRequest,
    build_semantic_catalog_submission_envelope,
)
from mhtml_etl_gateway.semantic_catalog_publisher import (
    CatalogPublisherError,
    CatalogPublisherEvidence,
    CatalogTransport,
    CatalogTransportResponse,
    publish_catalog_submission,
)


def _envelope():
    """Build a realistic value-free SAP-style graph handoff for publisher tests."""
    proposal = propose_schema(
        "a" * 64,
        (
            ProtectedColumnInput("MANDT", ("603", "603"), complete=True),
            ProtectedColumnInput("DUEDT", ("20260220", None), complete=False),
        ),
    )
    manifest = build_semantic_catalog_manifest(proposal, catalog_name="SAP VOC")
    return build_semantic_catalog_submission_envelope(
        manifest,
        tenant_id="tenant_cwl",
        actor="actor_catalog_steward",
        approval_reference="approval_2026_001",
    )


def _evidence() -> CatalogPublisherEvidence:
    """Return caller-owned proof for a successful publication."""
    return CatalogPublisherEvidence(
        actor_authenticated=True,
        tenant_authorized=True,
        approval_verified=True,
        immutable_audit_reference="audit://cwl/2026/001",
    )


class RecordingTransport:
    """Fake caller-owned transport that records request bodies only in the test."""

    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls = []

    def send(self, request):
        """Record one request and return or raise the next configured outcome."""
        self.calls.append(request)
        outcome = self.responses.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _accepted_responses(count: int) -> list[CatalogTransportResponse]:
    """Create deterministic HTTP acceptance evidence for ``count`` requests."""
    return [
        CatalogTransportResponse(
            status_code=201,
            remote_request_id=f"portal_request_{index}",
            accepted=True,
        )
        for index in range(count)
    ]


def test_publish_returns_value_free_remote_receipt_and_preserves_request_order() -> None:
    """A complete handoff records remote IDs without copying any request body."""
    envelope = _envelope()
    transport = RecordingTransport(_accepted_responses(len(envelope.requests)))

    receipt = publish_catalog_submission(envelope, transport, _evidence())
    payload = receipt.to_dict()

    assert receipt.accepted_request_count == len(envelope.requests)
    assert len(transport.calls) == len(envelope.requests)
    assert [item.request_index for item in receipt.request_receipts] == list(
        range(len(envelope.requests))
    )
    assert payload["privacy_mode"] == "value_free"
    assert payload["immutable_audit_reference"] == "audit://cwl/2026/001"
    assert all("body" not in item for item in payload["requests"])
    assert all(item["status_code"] == 201 for item in payload["requests"])


def test_evidence_serializes_its_control_proof() -> None:
    """Evidence serialization is explicit and contains no transport payload."""
    assert _evidence().to_dict() == {
        "actor_authenticated": True,
        "tenant_authorized": True,
        "approval_verified": True,
        "immutable_audit_reference": "audit://cwl/2026/001",
    }


def test_transport_protocol_method_is_explicitly_unimplemented() -> None:
    """The protocol documents the required adapter method without providing one."""
    request = CatalogWriteRequest("POST", "/graph/nodes", "semantic_catalog_write_1", {})
    with pytest.raises(NotImplementedError):
        CatalogTransport.send(object(), request)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("actor_authenticated", False, "actor_authentication_required"),
        ("tenant_authorized", False, "tenant_authorization_required"),
        ("approval_verified", False, "approval_verification_required"),
        ("immutable_audit_reference", "audit with spaces", "immutable_audit_reference_required"),
    ],
)
def test_evidence_requires_every_caller_owned_control(
    field: str,
    value: object,
    code: str,
) -> None:
    """Publication fails before transport when any governance proof is absent."""
    evidence = replace(_evidence(), **{field: value})

    with pytest.raises(CatalogPublisherError) as error:
        publish_catalog_submission(_envelope(), RecordingTransport([]), evidence)

    assert error.value.code == code
    assert error.value.accepted_request_count == 0


@pytest.mark.parametrize(
    ("status_code", "remote_request_id", "accepted", "code"),
    [
        (199, "portal_request_1", True, "remote_status_not_success"),
        (300, "portal_request_1", True, "remote_status_not_success"),
        (True, "portal_request_1", True, "remote_status_not_success"),
        (201, "portal_request_1", False, "remote_acceptance_required"),
        (201, "", True, "remote_request_id_required"),
        (201, "portal request", True, "remote_request_id_required"),
    ],
)
def test_transport_response_requires_success_and_remote_acceptance(
    status_code: object,
    remote_request_id: str,
    accepted: bool,
    code: str,
) -> None:
    """Remote status, explicit acceptance, and remote identity are all mandatory."""
    response = CatalogTransportResponse(
        status_code=status_code,  # type: ignore[arg-type]
        remote_request_id=remote_request_id,
        accepted=accepted,
    )

    with pytest.raises(CatalogPublisherError, match=f"catalog_publisher_{code}"):
        response.validate()


def test_transport_response_accepts_no_content_success() -> None:
    """A 204 response is valid when the transport supplies explicit remote evidence."""
    CatalogTransportResponse(
        status_code=204,
        remote_request_id="portal_request_204",
        accepted=True,
    ).validate()


@pytest.mark.parametrize("value", [0, 4097, True, "2"])
def test_publish_rejects_invalid_request_limits(value: object) -> None:
    """The publisher bounds fan-out and rejects ambiguous limit types."""
    with pytest.raises(CatalogPublisherError, match="invalid_request_limit"):
        publish_catalog_submission(
            _envelope(),
            RecordingTransport([]),
            _evidence(),
            max_requests=value,  # type: ignore[arg-type]
        )


def test_publish_rejects_invalid_envelope_and_transport() -> None:
    """The boundary requires the governed envelope and a callable transport."""
    with pytest.raises(CatalogPublisherError, match="invalid_envelope"):
        publish_catalog_submission(object(), RecordingTransport([]), _evidence())  # type: ignore[arg-type]
    with pytest.raises(CatalogPublisherError, match="transport_required"):
        publish_catalog_submission(_envelope(), object(), _evidence())  # type: ignore[arg-type]


def test_publish_rejects_empty_and_overlarge_envelopes() -> None:
    """Empty submissions and fan-out beyond the configured limit fail closed."""
    envelope = _envelope()
    empty = replace(envelope, requests=())
    with pytest.raises(CatalogPublisherError, match="no_catalog_requests"):
        publish_catalog_submission(empty, RecordingTransport([]), _evidence())
    with pytest.raises(CatalogPublisherError, match="request_limit_exceeded"):
        publish_catalog_submission(
            envelope,
            RecordingTransport(_accepted_responses(len(envelope.requests))),
            _evidence(),
            max_requests=1,
        )


@pytest.mark.parametrize(
    "catalog_request",
    [
        CatalogWriteRequest("PUT", "/graph/nodes", "semantic_catalog_write_1", {}),
        CatalogWriteRequest("POST", "/graph/unknown", "semantic_catalog_write_1", {}),
        CatalogWriteRequest("POST", "/graph/nodes", "bad-key", {}),
    ],
)
def test_publish_rejects_requests_outside_known_graph_contract(catalog_request) -> None:
    """Only portal node/edge POST requests with stable keys reach the transport."""
    envelope = replace(_envelope(), requests=(catalog_request,))

    with pytest.raises(CatalogPublisherError) as error:
        publish_catalog_submission(envelope, RecordingTransport([]), _evidence())

    assert error.value.code in {"invalid_catalog_request", "invalid_idempotency_key"}
    assert error.value.request_index == 0
    assert error.value.accepted_request_count == 0


def test_publish_rejects_non_request_items() -> None:
    """A malformed tuple member cannot bypass request validation."""
    envelope = replace(_envelope(), requests=(object(),))

    with pytest.raises(CatalogPublisherError) as error:
        publish_catalog_submission(envelope, RecordingTransport([]), _evidence())

    assert error.value.code == "invalid_catalog_request"
    assert error.value.to_dict() == {
        "error_code": "catalog_publisher_invalid_catalog_request",
        "request_index": 0,
        "accepted_request_count": 0,
    }


def test_publish_wraps_invalid_response_and_preserves_accepted_prefix() -> None:
    """A response shape failure reports the exact prefix requiring reconciliation."""
    envelope = _envelope()
    transport = RecordingTransport(
        [
            CatalogTransportResponse(201, "portal_request_0", True),
            object(),
        ]
    )

    with pytest.raises(CatalogPublisherError) as error:
        publish_catalog_submission(envelope, transport, _evidence())

    assert error.value.code == "invalid_transport_response"
    assert error.value.request_index == 1
    assert error.value.accepted_request_count == 1


def test_publish_wraps_transport_exceptions_without_reflecting_details() -> None:
    """Transport failures expose only a stable code, never provider error text."""
    envelope = _envelope()
    transport = RecordingTransport([RuntimeError("secret bearer token")])

    with pytest.raises(CatalogPublisherError) as error:
        publish_catalog_submission(envelope, transport, _evidence())

    assert error.value.code == "transport_failed"
    assert "secret bearer token" not in str(error.value)
    assert error.value.request_index == 0


def test_publish_wraps_remote_rejection_with_request_index() -> None:
    """A remote rejection is actionable without exposing the rejected payload."""
    envelope = _envelope()
    transport = RecordingTransport(
        [CatalogTransportResponse(403, "portal_request_0", False)]
    )

    with pytest.raises(CatalogPublisherError) as error:
        publish_catalog_submission(envelope, transport, _evidence())

    assert error.value.code == "remote_status_not_success"
    assert error.value.request_index == 0
