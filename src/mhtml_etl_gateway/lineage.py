"""Lineage helpers for immutable raw artifact tracking."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactLineage:
    """Opaque, immutable provenance record for a loaded source artifact."""

    source_artifact_path: str
    source_artifact_sha256: str
    source_artifact_size: int
    source_artifact_mtime_ns: int | None
    row_count: int
    table_name: str
    loaded_at: str

    def to_dict(self) -> dict[str, Any]:
        """Return lineage fields as a JSON-serializable mapping."""
        return asdict(self)


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of an in-memory artifact."""
    return hashlib.sha256(data).hexdigest()


def artifact_reference(sha256: str) -> str:
    """Return a stable, opaque lineage reference without a filesystem path."""
    if len(sha256) != 64 or any(
        char not in "0123456789abcdef" for char in sha256.lower()
    ):
        raise ValueError("artifact sha256 must be a 64-character hexadecimal digest")
    return f"artifact:{sha256[:16].lower()}"


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Hash a file incrementally so large source artifacts stay bounded in memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def build_lineage(
    path: Path | str,
    *,
    data: bytes | None = None,
    row_count: int,
    table_name: str,
    source_artifact_path: str | None = None,
    loaded_at: datetime | None = None,
) -> ArtifactLineage:
    """Build lineage from source bytes or a file while exposing only an opaque reference."""
    p = Path(path)
    if data is None:
        digest = sha256_file(p) if p.is_file() else ""
        size = p.stat().st_size if p.is_file() else 0
        mtime_ns = p.stat().st_mtime_ns if p.is_file() else None
    else:
        digest = sha256_bytes(data)
        size = len(data)
        mtime_ns = p.stat().st_mtime_ns if p.is_file() else None
    if not digest:
        raise ValueError("cannot build lineage without source artifact bytes")
    expected_reference = artifact_reference(digest)
    if source_artifact_path is not None and source_artifact_path != expected_reference:
        raise ValueError("source artifact reference does not match source digest")
    ts = loaded_at or datetime.now(timezone.utc)
    return ArtifactLineage(
        source_artifact_path=expected_reference,
        source_artifact_sha256=digest,
        source_artifact_size=size,
        source_artifact_mtime_ns=mtime_ns,
        row_count=row_count,
        table_name=table_name,
        loaded_at=ts.isoformat(),
    )


def write_lineage_json(lineage: ArtifactLineage, dest: Path | str) -> Path:
    """Write one deterministic, UTF-8 JSON lineage document and return its path."""
    out = Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(lineage.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out
