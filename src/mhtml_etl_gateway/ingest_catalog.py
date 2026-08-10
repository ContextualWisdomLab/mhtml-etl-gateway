"""Ingest catalog: which artifact sha256 was loaded into which table."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


CATALOG_TABLE = "mhtml_ingest_artifact"

# Constant DDL only — no user-controlled interpolation.
CATALOG_DDL = """
CREATE TABLE IF NOT EXISTS mhtml_ingest_artifact (
    source_artifact_sha256 TEXT NOT NULL,
    table_name TEXT NOT NULL,
    source_artifact_path TEXT NOT NULL,
    source_artifact_size BIGINT,
    row_count BIGINT NOT NULL,
    status TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_artifact_sha256, table_name)
);
""".strip()


@dataclass(frozen=True)
class CatalogEntry:
    source_artifact_sha256: str
    table_name: str
    source_artifact_path: str
    source_artifact_size: int | None
    row_count: int
    status: str
    loaded_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_artifact_sha256": self.source_artifact_sha256,
            "table_name": self.table_name,
            "source_artifact_path": self.source_artifact_path,
            "source_artifact_size": self.source_artifact_size,
            "row_count": self.row_count,
            "status": self.status,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
        }


def make_catalog_entry(
    *,
    sha256: str,
    table_name: str,
    path: str,
    size: int | None,
    row_count: int,
    status: str = "loaded",
) -> CatalogEntry:
    return CatalogEntry(
        source_artifact_sha256=sha256,
        table_name=table_name,
        source_artifact_path=path,
        source_artifact_size=size,
        row_count=row_count,
        status=status,
        loaded_at=datetime.now(timezone.utc),
    )
