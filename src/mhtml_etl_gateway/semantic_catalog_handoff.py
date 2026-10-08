"""Governed, transport-neutral submission envelopes for semantic catalog writes.

The envelope is the boundary between deterministic catalog content and an
application-owned publisher.  It makes tenant, actor, and approval context
explicit without adding raw MHTML values, network behavior, credentials, or
database state to the gateway library.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from mhtml_etl_gateway.semantic_catalog_connector import (
    EDGE_ENDPOINT,
    NODE_ENDPOINT,
    CatalogEdge,
    CatalogNode,
    SemanticCatalogManifest,
)

HANDOFF_CONTRACT_VERSION = "1.0.0"
_OPAQUE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")


def _canonical_json(value: Any) -> bytes:
    """Serialize handoff identity inputs deterministically as UTF-8 JSON."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _require_context_text(value: str, *, label: str, maximum: int = 256) -> str:
    """Validate human- or system-supplied context without normalizing identity."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    normalized = value.strip()
    if value != normalized:
        raise ValueError(f"{label} must not have leading or trailing whitespace")
    if not normalized:
        raise ValueError(f"{label} must be non-empty")
    if len(value) > maximum:
        raise ValueError(f"{label} is too long")
    if any(ord(character) < 0x20 or character == "\x7f" for character in value):
        raise ValueError(f"{label} contains a control character")
    return value


def _require_opaque_reference(value: str, *, label: str) -> str:
    """Validate an opaque tenant or approval reference used for idempotency."""
    normalized = _require_context_text(value, label=label, maximum=128)
    if _OPAQUE_REFERENCE.fullmatch(normalized) is None:
        raise ValueError(
            f"{label} must use letters, numbers, '.', ':', '/', '_' or '-'"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class CatalogWriteRequest:
    """One authenticated POST request planned for the portal graph API."""

    method: str
    path: str
    idempotency_key: str
    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return transport metadata and an actor-bound portal request body."""
        return {
            "method": self.method,
            "path": self.path,
            "idempotency_key": self.idempotency_key,
            "body": dict(self.body),
        }


@dataclass(frozen=True, slots=True)
class CatalogSubmissionEnvelope:
    """Deterministic approval and tenancy context for catalog write requests."""

    envelope_id: str
    contract_version: str
    target_system: str
    manifest_id: str
    tenant_id: str
    actor: str
    approval_reference: str
    requests: tuple[CatalogWriteRequest, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a value-free, auditable handoff envelope."""
        return {
            "envelope_id": self.envelope_id,
            "contract_version": self.contract_version,
            "target_system": self.target_system,
            "manifest_id": self.manifest_id,
            "tenant_id": self.tenant_id,
            "actor": self.actor,
            "approval_reference": self.approval_reference,
            "privacy_mode": "value_free",
            "requests": [request.to_dict() for request in self.requests],
        }


def _request_idempotency_key(
    *,
    manifest_id: str,
    tenant_id: str,
    approval_reference: str,
    path: str,
    body: dict[str, Any],
) -> str:
    """Build a stable, tenant- and approval-scoped write key."""
    identity = {
        "manifest_id": manifest_id,
        "tenant_id": tenant_id,
        "approval_reference": approval_reference,
        "path": path,
        "body": body,
    }
    digest = hashlib.sha256(_canonical_json(identity)).hexdigest()[:32]
    return f"semantic_catalog_write_{digest}"


def _node_request(
    node: CatalogNode,
    *,
    actor: str,
    manifest_id: str,
    tenant_id: str,
    approval_reference: str,
) -> CatalogWriteRequest:
    """Create the actor-bound request for one catalog node."""
    body = node.to_dict()
    body["actor"] = actor
    return CatalogWriteRequest(
        method="POST",
        path=NODE_ENDPOINT,
        idempotency_key=_request_idempotency_key(
            manifest_id=manifest_id,
            tenant_id=tenant_id,
            approval_reference=approval_reference,
            path=NODE_ENDPOINT,
            body=body,
        ),
        body=body,
    )


def _edge_request(
    edge: CatalogEdge,
    *,
    actor: str,
    manifest_id: str,
    tenant_id: str,
    approval_reference: str,
) -> CatalogWriteRequest:
    """Create the actor-bound request for one catalog edge."""
    body = edge.to_dict()
    body["actor"] = actor
    return CatalogWriteRequest(
        method="POST",
        path=EDGE_ENDPOINT,
        idempotency_key=_request_idempotency_key(
            manifest_id=manifest_id,
            tenant_id=tenant_id,
            approval_reference=approval_reference,
            path=EDGE_ENDPOINT,
            body=body,
        ),
        body=body,
    )


def build_semantic_catalog_submission_envelope(
    manifest: SemanticCatalogManifest,
    *,
    tenant_id: str,
    actor: str,
    approval_reference: str,
) -> CatalogSubmissionEnvelope:
    """Build an explicit approval-, tenant-, and actor-bound catalog handoff.

    The returned requests are ready for an application-owned HTTP adapter to
    send to the current Semantic Data Portal endpoints.  This function does
    not authenticate, authorize, send network traffic, retry, persist secrets,
    or mutate the input manifest.  Tenant and approval references are kept at
    the envelope boundary so a caller can bind them to its own route and audit
    system without leaking them into graph-node content.
    """
    normalized_tenant = _require_opaque_reference(tenant_id, label="tenant_id")
    normalized_actor = _require_context_text(actor, label="actor")
    normalized_approval = _require_opaque_reference(
        approval_reference,
        label="approval_reference",
    )
    requests = tuple(
        [
            *(
                _node_request(
                    node,
                    actor=normalized_actor,
                    manifest_id=manifest.manifest_id,
                    tenant_id=normalized_tenant,
                    approval_reference=normalized_approval,
                )
                for node in manifest.nodes
            ),
            *(
                _edge_request(
                    edge,
                    actor=normalized_actor,
                    manifest_id=manifest.manifest_id,
                    tenant_id=normalized_tenant,
                    approval_reference=normalized_approval,
                )
                for edge in manifest.edges
            ),
        ]
    )
    identity = {
        "contract_version": HANDOFF_CONTRACT_VERSION,
        "target_system": manifest.target_system,
        "manifest_id": manifest.manifest_id,
        "tenant_id": normalized_tenant,
        "actor": normalized_actor,
        "approval_reference": normalized_approval,
        "requests": [request.to_dict() for request in requests],
    }
    digest = hashlib.sha256(_canonical_json(identity)).hexdigest()[:32]
    return CatalogSubmissionEnvelope(
        envelope_id=f"semantic_catalog_handoff_{digest}",
        contract_version=HANDOFF_CONTRACT_VERSION,
        target_system=manifest.target_system,
        manifest_id=manifest.manifest_id,
        tenant_id=normalized_tenant,
        actor=normalized_actor,
        approval_reference=normalized_approval,
        requests=requests,
    )
