"""Value-free DBML visualization plans for the pg-erd-cloud API boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mhtml_etl_gateway.schema_inference import SchemaInferenceError, to_table_name
from mhtml_etl_gateway.schema_proposal import (
    ColumnProposal,
    PostgresType,
    SchemaProposal,
)
from mhtml_etl_gateway.sql_ident import UnsafeIdentifierError, require_safe_ident


PG_ERD_CONTRACT_VERSION = "1.0.0"
PG_ERD_TARGET_SYSTEM = "pg-erd-cloud"
PG_ERD_ENDPOINT = "/api/dbml/convert"

_DBML_TYPES = {
    PostgresType.TEXT: "text",
    PostgresType.BOOLEAN: "boolean",
    PostgresType.DATE: "date",
    PostgresType.BIGINT: "bigint",
    PostgresType.NUMERIC: "numeric",
}


@dataclass(frozen=True, slots=True, init=False)
class PgErdVisualizationPlan:
    """Transport-neutral, value-free request plan for pg-erd-cloud."""

    contract_version: str
    target_system: str
    source_hash_sha256: str
    schema_proposal_id: str
    dbml: str
    include_ddl: bool = False
    dialect: str = "postgresql"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Reject direct construction so callers cannot override the contract."""
        raise TypeError(
            "PgErdVisualizationPlan must be built with "
            "build_pg_erd_visualization_plan"
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the request shape accepted by pg-erd-cloud's DBML route."""
        return {
            "contract_version": self.contract_version,
            "target_system": self.target_system,
            "source_hash_sha256": self.source_hash_sha256,
            "schema_proposal_id": self.schema_proposal_id,
            "request": {
                "method": "POST",
                "path": PG_ERD_ENDPOINT,
                "body": {
                    "dbml": self.dbml,
                    "include_ddl": self.include_ddl,
                    "dialect": self.dialect,
                },
            },
        }


def _require_table_name(catalog_name: str) -> str:
    """Convert steward metadata to a bounded DBML-safe multiword identifier."""
    if not isinstance(catalog_name, str) or not catalog_name.strip():
        raise ValueError("catalog_name must be a non-empty string")
    display_name = catalog_name.strip()
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in display_name
    ):
        raise ValueError("catalog_name contains control characters")
    try:
        return require_safe_ident(to_table_name(display_name))
    except (SchemaInferenceError, UnsafeIdentifierError):
        raise ValueError("catalog_name must produce a safe table name") from None


def _dbml_column(column: ColumnProposal) -> str:
    """Render one allow-listed proposal column without notes or sample data."""
    if not isinstance(column.nullable, bool):
        raise ValueError("proposal column nullable flag is invalid")
    try:
        column_name = require_safe_ident(column.target_column_name)
        dbml_type = _DBML_TYPES[column.proposed_type]
    except (KeyError, TypeError, UnsafeIdentifierError):
        raise ValueError("proposal contains an unsafe column definition") from None
    setting = " [not null]" if not column.nullable else ""
    return f"  {column_name} {dbml_type}{setting}"


def build_pg_erd_visualization_plan(
    proposal: SchemaProposal,
    *,
    catalog_name: str,
) -> PgErdVisualizationPlan:
    """Build a deterministic DBML request plan from a value-free proposal.

    ``catalog_name`` is steward-provided display metadata.  Only normalized
    target identifiers, allow-listed types, and nullability settings enter the
    DBML.  The function performs no network, database, file, or authentication
    operation; a caller owns the authenticated request to pg-erd-cloud.
    """
    if not isinstance(proposal, SchemaProposal):
        raise ValueError("proposal must be a SchemaProposal")
    table_name = _require_table_name(catalog_name)
    columns = []
    for column in proposal.columns:
        if not isinstance(column, ColumnProposal):
            raise ValueError("proposal contains an invalid column")
        columns.append(_dbml_column(column))
    column_lines = "\n".join(columns)
    dbml = f"Table {table_name} {{\n{column_lines}\n}}"
    plan = object.__new__(PgErdVisualizationPlan)
    object.__setattr__(plan, "contract_version", PG_ERD_CONTRACT_VERSION)
    object.__setattr__(plan, "target_system", PG_ERD_TARGET_SYSTEM)
    object.__setattr__(plan, "source_hash_sha256", proposal.source_hash_sha256)
    object.__setattr__(plan, "schema_proposal_id", proposal.schema_proposal_id)
    object.__setattr__(plan, "dbml", dbml)
    object.__setattr__(plan, "include_ddl", False)
    object.__setattr__(plan, "dialect", "postgresql")
    return plan
