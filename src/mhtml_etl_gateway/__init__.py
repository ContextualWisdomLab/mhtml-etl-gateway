"""Public package interface for safe MHTML inspection and PostgreSQL ETL."""

from .batch import run_batch
from .errors import ErrorCode, MhtmlGatewayError
from .inspection import inspect_mhtml_bytes, inspect_mhtml_file
from .models import InspectionReport, ParseLimits
from .pipeline import (
    convert_mhtml_to_postgres,
    extract_table,
    propose_schema_from_mhtml,
)
from .pg_erd_connector import (
    PgErdVisualizationPlan,
    build_pg_erd_visualization_plan,
)
from .semantic_catalog_connector import (
    CatalogEdge,
    CatalogNode,
    SemanticCatalogManifest,
    build_semantic_catalog_manifest,
)
from .semantic_catalog_handoff import (
    CatalogSubmissionEnvelope,
    CatalogWriteRequest,
    build_semantic_catalog_submission_envelope,
)
from .semantic_catalog_publisher import (
    CatalogPublicationReceipt,
    CatalogPublisherError,
    CatalogPublisherEvidence,
    CatalogRequestReceipt,
    CatalogTransportResponse,
    publish_catalog_submission,
)
from .schema_proposal import SchemaProposal, SchemaProposalPolicy

__version__ = "0.4.0"

__all__ = [
    "ErrorCode",
    "InspectionReport",
    "MhtmlGatewayError",
    "ParseLimits",
    "__version__",
    "convert_mhtml_to_postgres",
    "extract_table",
    "propose_schema_from_mhtml",
    "SchemaProposal",
    "SchemaProposalPolicy",
    "PgErdVisualizationPlan",
    "build_pg_erd_visualization_plan",
    "inspect_mhtml_bytes",
    "inspect_mhtml_file",
    "run_batch",
    "CatalogEdge",
    "CatalogNode",
    "SemanticCatalogManifest",
    "build_semantic_catalog_manifest",
    "CatalogSubmissionEnvelope",
    "CatalogWriteRequest",
    "build_semantic_catalog_submission_envelope",
    "CatalogPublicationReceipt",
    "CatalogPublisherError",
    "CatalogPublisherEvidence",
    "CatalogRequestReceipt",
    "CatalogTransportResponse",
    "publish_catalog_submission",
]
