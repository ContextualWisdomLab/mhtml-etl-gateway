"""Bounded MIME parsing and RFC 2387 root HTML resolution."""

from __future__ import annotations

import codecs
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path

from .errors import ErrorCode, MhtmlGatewayError
from .models import Diagnostic, MhtmlDocument, ParseLimits

_KNOWN_TRANSFER_ENCODINGS = {
    "7bit",
    "8bit",
    "binary",
    "base64",
    "quoted-printable",
    "",
}
_BOM_ENCODINGS = (
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_BE, "utf-16"),
    (codecs.BOM_UTF16_LE, "utf-16"),
)

_CRITICAL_SINGLETON_HEADERS = (
    "Content-Type",
    "Content-ID",
    "Content-Location",
    "Content-Transfer-Encoding",
)
_CRITICAL_RELATED_PARAMETERS = {"boundary", "start", "type"}


def _raw_content_type_parameter_names(message: Message) -> list[str]:
    """Return raw Content-Type parameter names without splitting quoted text."""
    raw_value = next(
        (
            value
            for name, value in message.raw_items()
            if name.lower() == "content-type"
        ),
        "",
    )
    segments: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    comment_depth = 0
    for character in raw_value:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if character == "\\" and (quoted or comment_depth):
            escaped = True
            continue
        if comment_depth:
            if character == "(":
                comment_depth += 1
            elif character == ")":
                comment_depth -= 1
            continue
        if quoted:
            if character == '"':
                quoted = False
            current.append(character)
            continue
        if character == '"':
            quoted = True
            current.append(character)
        elif character == "(":
            comment_depth = 1
        elif character == ";":
            segments.append("".join(current))
            current = []
        else:
            current.append(character)
    segments.append("".join(current))

    names: list[str] = []
    for segment in segments[1:]:
        name, separator, _ = segment.partition("=")
        if separator:
            names.append(name.strip().lower())
    return names


def _normalize_content_id(value: str | None) -> str | None:
    """Normalize an optional Content-ID by removing surrounding brackets."""
    if value is None:
        return None
    normalized = value.strip().removeprefix("<").removesuffix(">").strip()
    return normalized or None


def _validate_mime_structure(
    message: Message,
    body_parts: list[Message],
) -> None:
    """Reject parser defects and ambiguous security-critical MIME metadata."""
    if message.get_content_type().lower() == "multipart/related":
        parameter_names = _raw_content_type_parameter_names(message)
        if any(
            parameter_names.count(name) > 1
            for name in _CRITICAL_RELATED_PARAMETERS
        ):
            raise MhtmlGatewayError(ErrorCode.INVALID_MIME)

    for part in [message, *body_parts]:
        if part.defects:
            raise MhtmlGatewayError(ErrorCode.INVALID_MIME)
        for header_name in _CRITICAL_SINGLETON_HEADERS:
            header_values = part.get_all(header_name, [])
            if len(header_values) > 1:
                raise MhtmlGatewayError(ErrorCode.INVALID_MIME)
            if header_name != "Content-Transfer-Encoding" and any(
                getattr(value, "defects", ()) for value in header_values
            ):
                raise MhtmlGatewayError(ErrorCode.INVALID_MIME)

    seen_content_ids: set[str] = set()
    for part in body_parts:
        content_id = _normalize_content_id(part.get("Content-ID"))
        if content_id is None:
            continue
        if content_id in seen_content_ids:
            raise MhtmlGatewayError(ErrorCode.AMBIGUOUS_HTML_ROOT)
        seen_content_ids.add(content_id)


def _bounded_body_parts(
    message: Message,
    limits: ParseLimits,
) -> list[Message]:
    """Return body entities in document order under count and depth budgets."""
    payload = message.get_payload()
    if not isinstance(payload, list):
        return []

    stack = [(part, 1) for part in reversed(payload)]
    body_parts: list[Message] = []
    while stack:
        part, depth = stack.pop()
        if depth > limits.max_mime_depth:
            raise MhtmlGatewayError(ErrorCode.MIME_NESTING_TOO_DEEP)
        body_parts.append(part)
        if len(body_parts) > limits.max_mime_parts:
            raise MhtmlGatewayError(ErrorCode.TOO_MANY_MIME_PARTS)
        child_payload = part.get_payload()
        if isinstance(child_payload, list):
            stack.extend(
                (child, depth + 1)
                for child in reversed(child_payload)
            )
    return body_parts


def _is_empty_related_container(message: Message) -> bool:
    """Return whether a related container has no direct root body entity."""
    if message.get_content_type().lower() != "multipart/related":
        return False
    payload = message.get_payload()
    if isinstance(payload, list):
        return not payload
    return isinstance(payload, str) and not payload.strip()


def _select_html_root(message: Message, parts: list[Message]) -> Message:
    """Select the authoritative HTML root using RFC 2387 semantics."""
    if (
        message.get_content_type().lower() == "text/html"
        and not message.is_multipart()
    ):
        return message
    if message.get_content_type().lower() != "multipart/related":
        raise MhtmlGatewayError(ErrorCode.INVALID_MIME)

    start = _normalize_content_id(message.get_param("start"))
    if start is not None:
        matches = [
            part
            for part in parts
            if _normalize_content_id(part.get("Content-ID")) == start
        ]
        if not matches:
            raise MhtmlGatewayError(ErrorCode.MISSING_HTML_ROOT)
        if len(matches) > 1:
            raise MhtmlGatewayError(ErrorCode.AMBIGUOUS_HTML_ROOT)
        root = matches[0]
        if root.is_multipart() or root.get_content_type().lower() != "text/html":
            raise MhtmlGatewayError(ErrorCode.MISSING_HTML_ROOT)
        return root

    direct_payload = message.get_payload()
    if (
        not isinstance(direct_payload, list)
        or not direct_payload
        or not isinstance(direct_payload[0], Message)
    ):
        raise MhtmlGatewayError(ErrorCode.MISSING_HTML_ROOT)
    root = direct_payload[0]
    if root.is_multipart() or root.get_content_type().lower() != "text/html":
        raise MhtmlGatewayError(ErrorCode.MISSING_HTML_ROOT)
    return root


def _related_type_diagnostics(
    message: Message,
    root: Message,
) -> tuple[Diagnostic, ...]:
    """Validate compound-object type and diagnose a known exporter omission."""
    if message.get_content_type().lower() != "multipart/related":
        return ()
    declared_type = message.get_param("type")
    if declared_type is None:
        return (
            Diagnostic(
                "missing_related_type",
                "The multipart/related type parameter was absent; the selected HTML root was validated directly",
            ),
        )
    if str(declared_type).strip().lower() != root.get_content_type().lower():
        raise MhtmlGatewayError(ErrorCode.INVALID_MIME)
    return ()


def _raw_payload_bytes(part: Message) -> bytes:
    """Return decoded payload bytes, preserving unknown identity encodings."""
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload
    raise MhtmlGatewayError(ErrorCode.HTML_DECODE_FAILED)


def _select_charset(part: Message, payload: bytes) -> str:
    """Resolve a declared charset or deterministic BOM/UTF-8 fallback."""
    declared = part.get_content_charset()
    if declared:
        try:
            codecs.lookup(declared)
        except LookupError as exc:
            raise MhtmlGatewayError(ErrorCode.UNKNOWN_CHARSET) from exc
        return declared
    for prefix, encoding in _BOM_ENCODINGS:
        if payload.startswith(prefix):
            return encoding
    return "utf-8"


def _decode_html(
    part: Message,
    limits: ParseLimits,
) -> tuple[str, tuple[Diagnostic, ...]]:
    """Decode selected HTML strictly and enforce its post-decode budget."""
    payload = _raw_payload_bytes(part)
    charset = _select_charset(part, payload)
    try:
        text = payload.decode(charset, errors="strict")
    except UnicodeDecodeError as exc:
        raise MhtmlGatewayError(ErrorCode.HTML_DECODE_FAILED) from exc
    if len(text) > limits.max_html_chars:
        raise MhtmlGatewayError(ErrorCode.HTML_TOO_LARGE)

    transfer_encoding = (
        part.get("Content-Transfer-Encoding") or ""
    ).strip().lower()
    diagnostics: tuple[Diagnostic, ...] = ()
    if transfer_encoding not in _KNOWN_TRANSFER_ENCODINGS:
        diagnostics = (
            Diagnostic(
                "identity_transfer_encoding",
                "A nonstandard Content-Transfer-Encoding was treated as identity bytes",
            ),
        )
    return text, diagnostics


def parse_mhtml_bytes(
    source_bytes: bytes,
    *,
    limits: ParseLimits | None = None,
) -> MhtmlDocument:
    """Parse untrusted bytes and return only the selected decoded HTML root."""
    effective_limits = limits or ParseLimits()
    if not isinstance(source_bytes, bytes):
        raise MhtmlGatewayError(ErrorCode.INVALID_MIME)
    if len(source_bytes) > effective_limits.max_source_bytes:
        raise MhtmlGatewayError(ErrorCode.SOURCE_TOO_LARGE)

    try:
        message = BytesParser(policy=policy.default).parsebytes(source_bytes)
    except RecursionError as exc:
        raise MhtmlGatewayError(ErrorCode.MIME_NESTING_TOO_DEEP) from exc

    if _is_empty_related_container(message):
        raise MhtmlGatewayError(ErrorCode.MISSING_HTML_ROOT)
    body_parts = _bounded_body_parts(message, effective_limits)
    _validate_mime_structure(message, body_parts)
    root = _select_html_root(message, body_parts)
    related_diagnostics = _related_type_diagnostics(message, root)
    html_text, decoding_diagnostics = _decode_html(root, effective_limits)
    return MhtmlDocument(
        html_text=html_text,
        root_content_type=root.get_content_type().lower(),
        root_content_location=root.get("Content-Location"),
        root_content_id=_normalize_content_id(root.get("Content-ID")),
        diagnostics=related_diagnostics + decoding_diagnostics,
    )


def parse_mhtml_file(
    source_path: str | Path,
    *,
    limits: ParseLimits | None = None,
) -> MhtmlDocument:
    """Read an MHTML file once and parse it with the byte-level contract."""
    path = Path(source_path)
    try:
        source_bytes = path.read_bytes()
    except OSError as exc:
        raise MhtmlGatewayError(ErrorCode.SOURCE_READ_FAILED) from exc
    return parse_mhtml_bytes(source_bytes, limits=limits)
