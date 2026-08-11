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


def _proposal() -> SchemaProposal:
    return propose_schema(
        "a" * 64,
        (
            ProtectedColumnInput("MANDT", ("603", "603"), complete=True),
            ProtectedColumnInput("DUEDT", ("20260220", None), complete=False),
        ),
    )


def test_manifest_matches_portal_requests_without_protected_values() -> None:
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


@pytest.mark.parametrize("catalog_name", ["", 42])
def test_manifest_rejects_missing_or_non_text_catalog_name(catalog_name: object) -> None:
    with pytest.raises(ValueError, match="catalog_name"):
        build_semantic_catalog_manifest(_proposal(), catalog_name=catalog_name)  # type: ignore[arg-type]
