from __future__ import annotations

import json

import pytest

from mhtml_etl_gateway.schema_proposal import (
    ProtectedColumnInput,
    SchemaProposal,
    propose_schema,
)
from mhtml_etl_gateway.semantic_catalog_connector import (
    CatalogEdge,
    CatalogNode,
    SemanticCatalogManifest,
    build_semantic_catalog_manifest,
)
from mhtml_etl_gateway.semantic_catalog_handoff import (
    CatalogSubmissionEnvelope,
    CatalogWriteRequest,
    build_semantic_catalog_submission_envelope,
)


def _proposal() -> SchemaProposal:
    """Return a small value-free schema proposal used by connector tests."""
    return propose_schema(
        "a" * 64,
        (
            ProtectedColumnInput("MANDT", ("603", "603"), complete=True),
            ProtectedColumnInput("DUEDT", ("20260220", None), complete=False),
        ),
    )


def test_manifest_matches_portal_requests_without_protected_values() -> None:
    """Manifest serialization preserves portal shapes without source values."""
    manifest = build_semantic_catalog_manifest(
        _proposal(),
        catalog_name="SAP VOC export",
    )
    payload = manifest.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert payload["target_system"] == "semantic-data-portal"
    assert payload["request_targets"] == {
        "nodes": "/graph/nodes",
        "edges": "/graph/edges",
    }
    assert len(payload["nodes"]) == 3
    assert len(payload["edges"]) == 2
    assert payload["nodes"][0]["kind"] == "dataset"
    assert payload["nodes"][0]["label"] == "SAP VOC export"
    assert payload["nodes"][0]["properties"]["privacy_mode"] == "value_free"
    assert payload["nodes"][0]["properties"]["review_required"] is True
    assert payload["edges"][0]["edge_type"] == "contains_column"
    assert "MANDT" not in encoded
    assert "603" not in encoded
    assert "20260220" not in encoded
    assert "a" * 64 in encoded


def test_manifest_identity_is_deterministic_and_order_sensitive() -> None:
    """Manifest IDs are stable for equal input and change when order changes."""
    proposal = _proposal()
    first = build_semantic_catalog_manifest(proposal, catalog_name="VOC")
    second = build_semantic_catalog_manifest(proposal, catalog_name="VOC")
    reordered = propose_schema(
        "a" * 64,
        tuple(
            reversed(
                (
                    ProtectedColumnInput("MANDT", ("603", "603"), complete=True),
                    ProtectedColumnInput("DUEDT", ("20260220", None), complete=False),
                )
            )
        ),
    )
    changed = build_semantic_catalog_manifest(reordered, catalog_name="VOC")

    assert first.to_dict() == second.to_dict()
    assert first.manifest_id != changed.manifest_id
    assert first.nodes[1].label == "client_code"
    assert changed.nodes[1].label == "due_date"


def test_manifest_trims_display_name_and_supports_empty_schema_shape() -> None:
    """Display names trim safely and empty schemas retain a dataset node."""
    empty_proposal = SchemaProposal(
        schema_proposal_id="schema_proposal_empty",
        proposal_version="1.0.0",
        source_hash_sha256="b" * 64,
        table_fingerprint_sha256="c" * 64,
        columns=(),
    )
    manifest = build_semantic_catalog_manifest(
        empty_proposal,
        catalog_name="  Empty source  ",
    )

    assert manifest.nodes[0].label == "Empty source"
    assert len(manifest.nodes) == 1
    assert manifest.edges == ()


def test_catalog_value_objects_serialize_portal_shapes() -> None:
    """Catalog value objects serialize their transport-compatible fields."""
    node = CatalogNode(
        node_id="mhtml_etl_dataset_demo",
        kind="dataset",
        label="Demo",
        properties={"privacy_mode": "value_free"},
        text="Demo schema proposal",
    )
    edge = CatalogEdge(
        edge_type="contains_column",
        source_id=node.node_id,
        target_id="mhtml_etl_dataset_demo_column_field",
        properties={},
    )
    manifest = SemanticCatalogManifest(
        manifest_id="semantic_catalog_manifest_demo",
        contract_version="1.0.0",
        target_system="semantic-data-portal",
        source_hash_sha256="d" * 64,
        schema_proposal_id="schema_proposal_demo",
        nodes=(node,),
        edges=(edge,),
    )

    assert node.to_dict()["kind"] == "dataset"
    assert edge.to_dict()["edge_type"] == "contains_column"
    assert manifest.to_dict()["manifest_id"] == "semantic_catalog_manifest_demo"


def test_submission_envelope_binds_actor_approval_and_tenant_without_values() -> None:
    """Submission envelopes bind governance context while excluding raw values."""
    manifest = build_semantic_catalog_manifest(_proposal(), catalog_name="VOC")
    envelope = build_semantic_catalog_submission_envelope(
        manifest,
        tenant_id="tenant_cwl_production",
        actor="svc_catalog_publisher",
        approval_reference="approval_2026_08_11_001",
    )
    payload = envelope.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert isinstance(envelope, CatalogSubmissionEnvelope)
    assert payload["privacy_mode"] == "value_free"
    assert payload["tenant_id"] == "tenant_cwl_production"
    assert payload["actor"] == "svc_catalog_publisher"
    assert payload["approval_reference"] == "approval_2026_08_11_001"
    assert len(payload["requests"]) == 5
    assert {request["path"] for request in payload["requests"]} == {
        "/graph/nodes",
        "/graph/edges",
    }
    assert all(request["method"] == "POST" for request in payload["requests"])
    assert all(
        request["body"]["actor"] == "svc_catalog_publisher"
        for request in payload["requests"]
    )
    assert len({request["idempotency_key"] for request in payload["requests"]}) == 5
    assert "MANDT" not in encoded
    assert "603" not in encoded
    assert "20260220" not in encoded


def test_submission_envelope_identity_changes_with_governance_context() -> None:
    """Tenant, actor, and approval changes produce distinct stable identities."""
    manifest = build_semantic_catalog_manifest(_proposal(), catalog_name="VOC")
    first = build_semantic_catalog_submission_envelope(
        manifest,
        tenant_id="tenant_a",
        actor="actor_a",
        approval_reference="approval_a",
    )
    second = build_semantic_catalog_submission_envelope(
        manifest,
        tenant_id="tenant_b",
        actor="actor_a",
        approval_reference="approval_a",
    )
    changed_approval = build_semantic_catalog_submission_envelope(
        manifest,
        tenant_id="tenant_a",
        actor="actor_a",
        approval_reference="approval_b",
    )
    changed_actor = build_semantic_catalog_submission_envelope(
        manifest,
        tenant_id="tenant_a",
        actor="actor_b",
        approval_reference="approval_a",
    )

    assert (
        first.to_dict()
        == build_semantic_catalog_submission_envelope(
            manifest,
            tenant_id="tenant_a",
            actor="actor_a",
            approval_reference="approval_a",
        ).to_dict()
    )
    assert first.envelope_id != second.envelope_id
    assert first.envelope_id != changed_approval.envelope_id
    assert first.envelope_id != changed_actor.envelope_id
    assert first.requests[0].idempotency_key != second.requests[0].idempotency_key
    assert (
        first.requests[0].idempotency_key
        != changed_approval.requests[0].idempotency_key
    )
    assert (
        first.requests[0].idempotency_key != changed_actor.requests[0].idempotency_key
    )


def test_catalog_write_request_serializes_its_transport_boundary() -> None:
    """A planned write request serializes method, path, key, and body exactly."""
    request = CatalogWriteRequest(
        method="POST",
        path="/graph/nodes",
        idempotency_key="semantic_catalog_write_demo",
        body={"node_id": "demo", "actor": "actor"},
    )

    assert request.to_dict() == {
        "method": "POST",
        "path": "/graph/nodes",
        "idempotency_key": "semantic_catalog_write_demo",
        "body": {"node_id": "demo", "actor": "actor"},
    }


@pytest.mark.parametrize("catalog_name", ["", 42])
def test_manifest_rejects_missing_or_non_text_catalog_name(
    catalog_name: object,
) -> None:
    """Catalog display names must be present text values."""
    with pytest.raises(ValueError, match="catalog_name"):
        build_semantic_catalog_manifest(_proposal(), catalog_name=catalog_name)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_id", ""),
        ("tenant_id", " tenant_cwl"),
        ("tenant_id", "tenant_cwl "),
        ("tenant_id", "tenant with spaces"),
        ("tenant_id", 42),
        ("actor", ""),
        ("actor", " svc_catalog_publisher"),
        ("actor", "svc_catalog_publisher "),
        ("actor", "actor\nforbidden"),
        ("actor", 42),
        ("approval_reference", ""),
        ("approval_reference", " approval_001"),
        ("approval_reference", "approval_001 "),
        ("approval_reference", "approval with spaces"),
        ("approval_reference", "a" * 129),
    ],
)
def test_submission_envelope_rejects_invalid_governance_context(
    field: str,
    value: str,
) -> None:
    """Malformed governance context is rejected instead of being normalized."""
    manifest = build_semantic_catalog_manifest(_proposal(), catalog_name="VOC")
    context = {
        "tenant_id": "tenant_cwl",
        "actor": "svc_catalog_publisher",
        "approval_reference": "approval_001",
    }
    context[field] = value

    with pytest.raises(ValueError, match=field):
        build_semantic_catalog_submission_envelope(manifest, **context)  # type: ignore[arg-type]
