"""Value-free Semantic Data Portal graph-ingestion manifest generation.

The connector is deliberately an in-process boundary.  It creates the JSON
requests that a caller may submit to Semantic Data Portal's ``/graph/nodes``
and ``/graph/edges`` endpoints, but it never performs network I/O or stores
protected source data.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from mhtml_etl_gateway.schema_proposal import SchemaProposal

CONNECTOR_CONTRACT_VERSION = "1.0.0"
TARGET_SYSTEM = "semantic-data-portal"
NODE_ENDPOINT = "/graph/nodes"
EDGE_ENDPOINT = "/graph/edges"
_DATASET_NODE_PREFIX = "mhtml_etl_dataset_"


def _canonical_json(value: Any) -> bytes:
    """Serialize connector identity inputs deterministically as UTF-8 JSON."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _require_catalog_name(value: str) -> str:
    """Validate and trim a steward-provided catalog display name."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("catalog_name must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class CatalogNode:
    """One request-compatible, value-free Semantic Data Portal graph node."""

    node_id: str
    kind: str
    label: str
    properties: dict[str, Any]
    text: str

    def to_dict(self) -> dict[str, Any]:
        """Return the node shape accepted by the portal graph endpoint."""
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "label": self.label,
            "properties": dict(self.properties),
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class CatalogEdge:
    """One request-compatible relation between value-free graph nodes."""

    edge_type: str
    source_id: str
    target_id: str
    properties: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the edge shape accepted by the portal graph endpoint."""
        return {
            "edge_type": self.edge_type,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True, slots=True)
class SemanticCatalogManifest:
    """Deterministic graph-ingestion bundle for one schema proposal."""

    manifest_id: str
    contract_version: str
    target_system: str
    source_hash_sha256: str
    schema_proposal_id: str
    nodes: tuple[CatalogNode, ...]
    edges: tuple[CatalogEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the complete value-free connector manifest."""
        return {
            "manifest_id": self.manifest_id,
            "contract_version": self.contract_version,
            "target_system": self.target_system,
            "source_hash_sha256": self.source_hash_sha256,
            "schema_proposal_id": self.schema_proposal_id,
            "request_targets": {
                "nodes": NODE_ENDPOINT,
                "edges": EDGE_ENDPOINT,
            },
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


def _manifest_identity(
    *,
    source_hash_sha256: str,
    schema_proposal_id: str,
    nodes: tuple[CatalogNode, ...],
    edges: tuple[CatalogEdge, ...],
) -> dict[str, Any]:
    """Return manifest fields that participate in the stable identity."""
    return {
        "contract_version": CONNECTOR_CONTRACT_VERSION,
        "target_system": TARGET_SYSTEM,
        "source_hash_sha256": source_hash_sha256,
        "schema_proposal_id": schema_proposal_id,
        "nodes": [node.to_dict() for node in nodes],
        "edges": [edge.to_dict() for edge in edges],
    }


def build_semantic_catalog_manifest(
    proposal: SchemaProposal,
    *,
    catalog_name: str,
) -> SemanticCatalogManifest:
    """Build a deterministic, value-free manifest for Semantic Data Portal.

    ``catalog_name`` is steward-provided display metadata.  Protected source
    headers and sample values are taken only from the already value-free
    ``SchemaProposal`` output: target names, hashes, aggregate evidence, and
    review reasons.  The returned manifest is suitable for an HTTP client to
    submit one node and edge request at a time, but this function performs no
    network, database, LLM, or file operation.
    """
    display_name = _require_catalog_name(catalog_name)
    dataset_node_id = f"{_DATASET_NODE_PREFIX}{proposal.schema_proposal_id.removeprefix('schema_proposal_')}"
    review_required = any(column.review_reasons for column in proposal.columns)
    dataset_node = CatalogNode(
        node_id=dataset_node_id,
        kind="dataset",
        label=display_name,
        properties={
            "connector_contract_version": CONNECTOR_CONTRACT_VERSION,
            "source_system": "mhtml-etl-gateway",
            "source_hash_sha256": proposal.source_hash_sha256,
            "schema_proposal_id": proposal.schema_proposal_id,
            "proposal_version": proposal.proposal_version,
            "table_fingerprint_sha256": proposal.table_fingerprint_sha256,
            "column_count": len(proposal.columns),
            "review_required": review_required,
            "privacy_mode": "value_free",
        },
        text=f"{display_name} schema proposal",
    )

    column_nodes: list[CatalogNode] = []
    edges: list[CatalogEdge] = []
    for column in proposal.columns:
        column_node_id = f"{dataset_node_id}_column_{column.target_column_name}"
        column_nodes.append(
            CatalogNode(
                node_id=column_node_id,
                kind="column",
                label=column.target_column_name,
                properties={
                    "connector_contract_version": CONNECTOR_CONTRACT_VERSION,
                    "source_header_hash_sha256": column.source_header_hash_sha256,
                    "target_column_name": column.target_column_name,
                    "proposed_type": column.proposed_type.value,
                    "nullable": column.nullable,
                    "non_null_count": column.non_null_count,
                    "distinct_count": column.distinct_count,
                    "maximum_text_length": column.maximum_text_length,
                    "maximum_numeric_precision": column.maximum_numeric_precision,
                    "maximum_numeric_scale": column.maximum_numeric_scale,
                    "review_reasons": list(column.review_reasons),
                    "privacy_mode": "value_free",
                },
                text=(
                    f"{display_name} {column.target_column_name} "
                    f"{column.proposed_type.value}"
                ),
            )
        )
        edges.append(
            CatalogEdge(
                edge_type="contains_column",
                source_id=dataset_node_id,
                target_id=column_node_id,
                properties={
                    "schema_proposal_id": proposal.schema_proposal_id,
                    "privacy_mode": "value_free",
                },
            )
        )

    nodes = (dataset_node, *column_nodes)
    edge_tuple = tuple(edges)
    identity = _manifest_identity(
        source_hash_sha256=proposal.source_hash_sha256,
        schema_proposal_id=proposal.schema_proposal_id,
        nodes=nodes,
        edges=edge_tuple,
    )
    manifest_digest = hashlib.sha256(_canonical_json(identity)).hexdigest()
    return SemanticCatalogManifest(
        manifest_id=f"semantic_catalog_manifest_{manifest_digest[:32]}",
        contract_version=CONNECTOR_CONTRACT_VERSION,
        target_system=TARGET_SYSTEM,
        source_hash_sha256=proposal.source_hash_sha256,
        schema_proposal_id=proposal.schema_proposal_id,
        nodes=nodes,
        edges=edge_tuple,
    )
