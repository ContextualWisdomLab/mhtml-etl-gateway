"""Stable, nonreflecting failures for protected schema proposal input."""

from __future__ import annotations

from enum import Enum


class SchemaProposalErrorCode(str, Enum):
    """Machine-readable failures exposed by the schema proposal boundary."""

    INVALID_POLICY = "invalid_policy"
    INVALID_TABLE_LABEL = "invalid_table_label"
    INVALID_COLUMN = "invalid_column"
    TOO_MANY_COLUMNS = "too_many_columns"
    TOO_MANY_SAMPLES = "too_many_samples"
    VALUE_TOO_LARGE = "value_too_large"
    UNSUPPORTED_VALUE = "unsupported_value"


_SAFE_ERROR_MESSAGES: dict[SchemaProposalErrorCode, str] = {
    SchemaProposalErrorCode.INVALID_POLICY: "Schema proposal policy is invalid",
    SchemaProposalErrorCode.INVALID_TABLE_LABEL: "Protected table label is invalid",
    SchemaProposalErrorCode.INVALID_COLUMN: "Protected column evidence is invalid",
    SchemaProposalErrorCode.TOO_MANY_COLUMNS: "Schema proposal exceeds the column limit",
    SchemaProposalErrorCode.TOO_MANY_SAMPLES: "Column evidence exceeds the sample limit",
    SchemaProposalErrorCode.VALUE_TOO_LARGE: "Protected schema evidence exceeds a size limit",
    SchemaProposalErrorCode.UNSUPPORTED_VALUE: (
        "Protected schema evidence contains an unsupported value"
    ),
}


class SchemaProposalError(Exception):
    """Fail-closed proposal error with a fixed, nonreflecting public message."""

    def __init__(self, code: SchemaProposalErrorCode) -> None:
        """Create an error without retaining caller-controlled detail."""
        self.code = code
        self.message = _SAFE_ERROR_MESSAGES[code]
        super().__init__(f"{code.value}: {self.message}")

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-ready error representation without protected values."""
        return {"error_code": self.code.value, "message": self.message}
