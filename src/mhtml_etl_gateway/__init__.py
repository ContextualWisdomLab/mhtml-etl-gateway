"""Public package interface for MHTML ETL Gateway."""

from __future__ import annotations

from .errors import ErrorCode, MhtmlGatewayError
from .inspection import inspect_mhtml_bytes, inspect_mhtml_file
from .models import InspectionReport, ParseLimits

__version__ = "0.1.0"

__all__ = [
    "ErrorCode",
    "InspectionReport",
    "MhtmlGatewayError",
    "ParseLimits",
    "__version__",
    "inspect_mhtml_bytes",
    "inspect_mhtml_file",
]
