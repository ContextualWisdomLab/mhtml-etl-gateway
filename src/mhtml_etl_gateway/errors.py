"""Stable, nonreflecting error contracts for untrusted MHTML failures."""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Machine-readable failure codes exposed by the parser and CLI."""

    INVALID_ARGUMENT = "invalid_argument"
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
    SCHEMA_PROPOSAL_FAILED = "schema_proposal_failed"


_SAFE_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_ARGUMENT: "Argument is invalid",
    ErrorCode.SOURCE_TOO_LARGE: "MHTML source exceeds the configured size limit",
    ErrorCode.SOURCE_READ_FAILED: "MHTML source could not be read",
    ErrorCode.INVALID_MIME: "MHTML input is invalid",
    ErrorCode.TOO_MANY_MIME_PARTS: "MHTML input exceeds the configured entity limit",
    ErrorCode.MIME_NESTING_TOO_DEEP: "MHTML input exceeds the configured nesting limit",
    ErrorCode.MISSING_HTML_ROOT: "MHTML input has no valid HTML root",
    ErrorCode.AMBIGUOUS_HTML_ROOT: "MHTML input is ambiguous",
    ErrorCode.UNKNOWN_CHARSET: "MHTML input declares an unsupported character set",
    ErrorCode.HTML_DECODE_FAILED: "MHTML HTML content could not be decoded",
    ErrorCode.HTML_TOO_LARGE: "Decoded HTML exceeds the configured size limit",
    ErrorCode.TOO_MANY_TABLES: "HTML contains too many tables",
    ErrorCode.TOO_MANY_ROWS: "HTML table exceeds the configured row limit",
    ErrorCode.TOO_MANY_COLUMNS: "HTML table exceeds the configured column limit",
    ErrorCode.TOO_MANY_CELLS: "HTML tables exceed the configured cell limit",
    ErrorCode.CELL_TEXT_TOO_LARGE: "HTML table cell exceeds the configured text limit",
    ErrorCode.NESTED_TABLE: "Nested HTML tables are not supported",
    ErrorCode.INVALID_TABLE_SPAN: "HTML table span is invalid",
    ErrorCode.SCHEMA_PROPOSAL_FAILED: "Schema proposal could not be produced",
}


class MhtmlGatewayError(Exception):
    """Expected fail-closed error with a fixed, approved-safe public message."""

    def __init__(self, code: ErrorCode, detail: str | None = None) -> None:
        """Initialize an error while deliberately discarding untrusted detail."""
        del detail
        self.code = code
        self.message = _SAFE_MESSAGES[code]
        super().__init__(f"{code.value}: {self.message}")

    def to_dict(self) -> dict[str, str]:
        """Return the fixed JSON representation used by public interfaces."""
        return {"error_code": self.code.value, "message": self.message}
