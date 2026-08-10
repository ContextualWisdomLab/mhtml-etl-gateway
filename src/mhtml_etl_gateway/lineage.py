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
    source_artifact_path: str
    source_artifact_sha256: str
    source_artifact_size: int
    source_artifact_mtime_ns: int | None
    row_count: int
    table_name: str
    loaded_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
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
    loaded_at: datetime | None = None,
) -> ArtifactLineage:
    p = Path(path)
    if data is None:
        digest = sha256_file(p) if p.is_file() else ""
        size = p.stat().st_size if p.is_file() else 0
        mtime_ns = p.stat().st_mtime_ns if p.is_file() else None
    else:
        digest = sha256_bytes(data)
        size = len(data)
        mtime_ns = p.stat().st_mtime_ns if p.is_file() else None
    ts = loaded_at or datetime.now(timezone.utc)
    return ArtifactLineage(
        source_artifact_path=str(p),
        source_artifact_sha256=digest,
        source_artifact_size=size,
        source_artifact_mtime_ns=mtime_ns,
        row_count=row_count,
        table_name=table_name,
        loaded_at=ts.isoformat(),
    )


def write_lineage_json(lineage: ArtifactLineage, dest: Path | str) -> Path:
    out = Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lineage.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
