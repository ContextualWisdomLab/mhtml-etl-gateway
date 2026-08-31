"""MIME multipart extraction from MHTML (no script execution, no network)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable


class MhtmlParseError(ValueError):
    """Fail-closed parse error for malformed or empty MHTML."""


@dataclass(frozen=True)
class MimePart:
    """Decoded MIME part metadata and payload selected from an MHTML archive."""

    content_type: str
    content_location: str | None
    payload: bytes


def _decode_part_payload(part) -> bytes | None:
    """Decode a MIME part payload, tolerating non-standard CTE values (SAP Excel)."""
    raw = part.get_payload(decode=True)
    if isinstance(raw, bytes) and raw:
        return raw
    payload = part.get_payload(decode=False)
    if isinstance(payload, bytes) and payload:
        return payload
    if isinstance(payload, str) and payload:
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.encode(charset, errors="replace")
        except LookupError:
            return payload.encode("utf-8", errors="replace")
    return None


def _looks_like_mhtml(data: bytes) -> bool:
    """Heuristic: MHTML/MIME archive or bare HTML worksheet."""
    head = data[:4096].lower()
    if b"mime-version:" in head or b"content-type:" in head:
        return True
    if b"multipart/" in head:
        return True
    if re.search(br"<html[\s>]", head, re.I) and (
        b"<table" in data[:65536].lower() or b"multipart" in head
    ):
        return True
    return False


def parse_mhtml_parts(data: bytes) -> list[MimePart]:
    """Parse MHTML/MIME multipart bytes into ordered parts.

    Does not execute HTML/JS and does not fetch external resources.
    Raises MhtmlParseError on empty input or when no usable parts exist.
    """
    if not data or not data.strip():
        raise MhtmlParseError("empty MHTML input")

    if not _looks_like_mhtml(data):
        raise MhtmlParseError("input is not MHTML/MIME or HTML table content")

    msg = BytesParser(policy=policy.default).parsebytes(data)
    parts: list[MimePart] = []

    walk: Iterable = msg.walk() if msg.is_multipart() else [msg]
    for part in walk:
        if part.get_content_maintype() == "multipart":
            continue
        payload = _decode_part_payload(part)
        if payload is None:
            continue
        parts.append(
            MimePart(
                content_type=part.get_content_type() or "application/octet-stream",
                content_location=part.get("Content-Location"),
                payload=payload,
            )
        )

    if not parts:
        if re.search(br"<html[\s>]", data, re.I):
            parts.append(
                MimePart(
                    content_type="text/html",
                    content_location=None,
                    payload=data,
                )
            )
        else:
            raise MhtmlParseError("no MIME parts found in MHTML")

    return parts


def extract_html_bytes(data: bytes) -> bytes:
    """Return the primary HTML part payload from MHTML bytes (fail-closed).

    Returns a view/reference to the part payload (one HTML buffer), not a second
    full-file re-encode of the entire MHTML when the HTML part is already decoded.
    """
    parts = parse_mhtml_parts(data)
    html_parts = [p for p in parts if p.content_type == "text/html"]
    if not html_parts:
        for p in parts:
            head = p.payload[:8192].lower()
            if b"<html" in head or b"<table" in head:
                return p.payload
        raise MhtmlParseError("no HTML part found in MHTML")
    # Prefer the largest HTML part (worksheet body) — single buffer, no copy.
    return max(html_parts, key=lambda p: len(p.payload)).payload


def read_mhtml_file(path: str | Path, *, chunk_size: int = 8 * 1024 * 1024) -> bytes:
    """Read an MHTML file once via buffered chunks (single buffer assembly).

    Avoids holding multiple independent full-file copies from layered readers.
    For streaming table extraction, use :func:`extract_html_bytes` then
    :func:`mhtml_etl_gateway.html_table_extractor.extract_primary_table` which
    feeds the HTML parser in chunks without building intermediate table copies
    beyond the extracted cell data.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"MHTML file not found: {p}")
    # Single open; accumulate into one bytearray then freeze once.
    buf = bytearray()
    with p.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            buf.extend(chunk)
    return bytes(buf)


def extract_html_from_path(path: str | Path) -> tuple[bytes, bytes]:
    """Read file once; return (raw_mhtml, html_part) without re-reading disk."""
    raw = read_mhtml_file(path)
    return raw, extract_html_bytes(raw)
