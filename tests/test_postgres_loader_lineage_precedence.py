"""Regression coverage for immutable system-lineage fields in row records."""

from __future__ import annotations

from datetime import datetime

from mhtml_etl_gateway.postgres_loader import _build_row_records
from mhtml_etl_gateway.schema_inference import PG_TEXT, ColumnSpec, TableSchema


def test_build_row_records_system_lineage_wins_on_business_name_collision() -> None:
    """Business columns must never overwrite trusted lineage metadata."""
    loaded_at = datetime(2026, 9, 12, 11, 30, 0)
    schema = TableSchema(
        table_name="collision_rows",
        columns=[
            ColumnSpec(
                "SOURCE_ARTIFACT_PATH",
                "source_artifact_path",
                PG_TEXT,
            )
        ],
    )

    records = _build_row_records(
        schema,
        [["attacker-controlled-path"]],
        source_artifact_path="artifact:trusted-source",
        source_artifact_sha256="a" * 64,
        start_row_number=7,
        loaded_at=loaded_at,
    )

    assert records == [
        {
            "source_artifact_path": "artifact:trusted-source",
            "source_artifact_sha256": "a" * 64,
            "source_row_number": 7,
            "loaded_at": loaded_at,
        }
    ]
