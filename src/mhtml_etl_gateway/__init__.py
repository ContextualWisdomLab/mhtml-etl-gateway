"""Public package interface for safe MHTML inspection and PostgreSQL ETL."""

from .batch import run_batch
from .errors import ErrorCode, MhtmlGatewayError
from .inspection import inspect_mhtml_bytes, inspect_mhtml_file
from .models import InspectionReport, ParseLimits
from .pipeline import convert_mhtml_to_postgres, extract_table
from .semantic_catalog_connector import (
    CatalogEdge,
    CatalogNode,
    SemanticCatalogManifest,
    build_semantic_catalog_manifest,
)

__version__ = "0.3.0"

__all__ = [
    "ErrorCode",
    "InspectionReport",
    "MhtmlGatewayError",
    "ParseLimits",
    "__version__",
    "convert_mhtml_to_postgres",
    "extract_table",
    "inspect_mhtml_bytes",
    "inspect_mhtml_file",
    "run_batch",
    "CatalogEdge",
    "CatalogNode",
    "SemanticCatalogManifest",
    "build_semantic_catalog_manifest",
]
