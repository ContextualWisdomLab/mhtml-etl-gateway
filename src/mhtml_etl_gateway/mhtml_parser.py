"""MIME multipart extraction from MHTML bytes (no script execution, no network)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from typing import Iterable


class MhtmlParseError(ValueError):
    """Fail-closed parse error for malformed or empty MHTML."""


@dataclass(frozen=True)
class MimePart:
    content_type: str
    content_location: str | None
    payload: bytes


def _decode_part_payload(part) -> bytes | None:
    """Decode a MIME part payload, tolerating non-standard CTE values (SAP Excel)."""
    raw = part.get_payload(decode=True)
    if isinstance(raw, bytes) and raw:
        return raw
    # SAP ALV sometimes sets Content-Transfer-Encoding: text/html (invalid).
    # Fall back to the undecoded payload string/bytes.
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
        # Fallback: treat entire body as a single HTML document if markers exist.
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
    """Return the primary HTML part payload from MHTML bytes (fail-closed)."""
    parts = parse_mhtml_parts(data)
    html_parts = [p for p in parts if p.content_type == "text/html"]
    if not html_parts:
        # Prefer any part that looks like HTML.
        for p in parts:
            if b"<html" in p.payload[:4096].lower() or b"<table" in p.payload[:8192].lower():
                return p.payload
        raise MhtmlParseError("no HTML part found in MHTML")
    # Prefer the largest HTML part (worksheet body).
    return max(html_parts, key=lambda p: len(p.payload)).payload
