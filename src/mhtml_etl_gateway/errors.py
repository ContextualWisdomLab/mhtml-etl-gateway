"""Stable error contracts for untrusted MHTML input failures."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Machine-readable failure codes exposed by the parser and CLI."""

    SOURCE_TOO_LARGE = "source_too_large"
    SOURCE_READ_FAILED = "source_read_failed"
    INVALID_MIME = "invalid_mime"
    TOO_MANY_MIME_PARTS = "too_many_mime_parts"
    MIME_NESTING_TOO_DEEP = "mime_nesting_too_deep"
    MISSING_HTML_ROOT = "missing_html_root"
    AMBIGUOUS_HTML_ROOT = "ambiguous_html_root"
    UNKNOWN_CHARSET = "unknown_charset"
    HTML_DECODE_FAILED = "html_decode_failed"
    HTML_TOO_LARGE = "html_too_large"
    TOO_MANY_TABLES = "too_many_tables"
    TOO_MANY_ROWS = "too_many_rows"
    TOO_MANY_COLUMNS = "too_many_columns"
    TOO_MANY_CELLS = "too_many_cells"
    CELL_TEXT_TOO_LARGE = "cell_text_too_large"
    NESTED_TABLE = "nested_table"
    INVALID_TABLE_SPAN = "invalid_table_span"


class MhtmlGatewayError(Exception):
    """Expected fail-closed error raised for unsafe or malformed source input."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        """Initialize an error with a stable code and explanatory message."""
        self.code = code
        self.message = message
        super().__init__(f"{code.value}: {message}")

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-ready representation used by the CLI."""
        return {"error_code": self.code.value, "message": self.message}
