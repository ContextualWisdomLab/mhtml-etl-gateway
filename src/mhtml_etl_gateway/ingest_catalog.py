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
    load_status_code TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_artifact_sha256, table_name)
);
""".strip()

# A constant migration for installations created before the multiword
# status-column policy was enforced. It never interpolates a caller value and
# is safe to run after CATALOG_DDL on every startup. Ambiguous dual-column
# states fail closed instead of silently selecting one source of truth.
CATALOG_STATUS_MIGRATION_DDL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'mhtml_ingest_artifact'
          AND column_name = 'status'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'mhtml_ingest_artifact'
          AND column_name = 'load_status_code'
    ) THEN
        RAISE EXCEPTION
            'catalog contains both status and load_status_code columns';
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'mhtml_ingest_artifact'
          AND column_name = 'status'
    ) THEN
        ALTER TABLE mhtml_ingest_artifact
            RENAME COLUMN status TO load_status_code;
    END IF;
END
$$;
""".strip()

# Operators run this explicit down migration in the same transaction before
# reverting to an application release that still reads the legacy column.
CATALOG_STATUS_ROLLBACK_DDL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'mhtml_ingest_artifact'
          AND column_name = 'status'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'mhtml_ingest_artifact'
          AND column_name = 'load_status_code'
    ) THEN
        RAISE EXCEPTION
            'catalog contains both status and load_status_code columns';
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'mhtml_ingest_artifact'
          AND column_name = 'load_status_code'
    ) THEN
        ALTER TABLE mhtml_ingest_artifact
            RENAME COLUMN load_status_code TO status;
    END IF;
END
$$;
""".strip()


@dataclass(frozen=True)
class CatalogEntry:
    """Immutable catalog record for one artifact-to-table load."""

    source_artifact_sha256: str
    table_name: str
    source_artifact_path: str
    source_artifact_size: int | None
    row_count: int
    load_status_code: str
    loaded_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the catalog record using the established pipeline wire keys."""
        return {
            "source_artifact_sha256": self.source_artifact_sha256,
            "table_name": self.table_name,
            "source_artifact_path": self.source_artifact_path,
            "source_artifact_size": self.source_artifact_size,
            "row_count": self.row_count,
            "status": self.load_status_code,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
        }


def make_catalog_entry(
    *,
    source_artifact_sha256: str | None = None,
    table_name: str,
    source_artifact_path: str | None = None,
    source_artifact_size: int | None = None,
    row_count: int,
    load_status_code: str | None = None,
    **legacy_catalog_fields: Any,
) -> CatalogEntry:
    """Create a catalog record while translating deprecated legacy keywords."""
    if "sha256" in legacy_catalog_fields:
        if source_artifact_sha256 is not None:
            raise TypeError("conflicting source artifact digest fields")
        source_artifact_sha256 = legacy_catalog_fields.pop("sha256")
    if "path" in legacy_catalog_fields:
        if source_artifact_path is not None:
            raise TypeError("conflicting source artifact path fields")
        source_artifact_path = legacy_catalog_fields.pop("path")
    if "size" in legacy_catalog_fields:
        if source_artifact_size is not None:
            raise TypeError("conflicting source artifact size fields")
        source_artifact_size = legacy_catalog_fields.pop("size")
    if "status" in legacy_catalog_fields:
        if load_status_code is not None:
            raise TypeError("conflicting load status fields")
        load_status_code = legacy_catalog_fields.pop("status")
    if legacy_catalog_fields:
        raise TypeError("unexpected legacy catalog field")
    if source_artifact_sha256 is None:
        raise TypeError("source_artifact_sha256 is required")
    if source_artifact_path is None:
        raise TypeError("source_artifact_path is required")

    return CatalogEntry(
        source_artifact_sha256=source_artifact_sha256,
        table_name=table_name,
        source_artifact_path=source_artifact_path,
        source_artifact_size=source_artifact_size,
        row_count=row_count,
        load_status_code=load_status_code or "loaded",
        loaded_at=datetime.now(timezone.utc),
    )
