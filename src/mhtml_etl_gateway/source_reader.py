"""Bounded local-source reads shared by file-based inspection entry points."""

from __future__ import annotations

from pathlib import Path

from .errors import ErrorCode, MhtmlGatewayError
from .models import ParseLimits

_READ_CHUNK_BYTES = 1024 * 1024


def _read_bounded_source(
    source_path: str | Path,
    *,
    limits: ParseLimits | None = None,
) -> bytes:
    """Read at most one byte beyond the source budget without reflecting its path."""
    effective_limits = limits or ParseLimits()
    source = bytearray()
    path = Path(source_path)
    try:
        with path.open("rb") as source_file:
            while len(source) <= effective_limits.max_source_bytes:
                remaining = effective_limits.max_source_bytes + 1 - len(source)
                chunk = source_file.read(min(_READ_CHUNK_BYTES, remaining))
                if not chunk:
                    break
                source.extend(chunk)
    except OSError as exc:
        raise MhtmlGatewayError(ErrorCode.SOURCE_READ_FAILED) from exc

    if len(source) > effective_limits.max_source_bytes:
        raise MhtmlGatewayError(ErrorCode.SOURCE_TOO_LARGE)
    return bytes(source)
