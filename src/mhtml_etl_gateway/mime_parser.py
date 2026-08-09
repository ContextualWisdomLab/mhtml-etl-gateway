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


def _validate_mime_structure(message: Message) -> None:
    """Reject parser defects and duplicate security-critical MIME metadata."""
    # Inspect raw parameters before the structured parser can collapse a
    # duplicate or malformed field into one selected value.
    if message.get_content_type().lower() == "multipart/related":
        parameter_names = _raw_content_type_parameter_names(message)
        if any(
            parameter_names.count(name) > 1
            for name in _CRITICAL_RELATED_PARAMETERS
        ):
            raise MhtmlGatewayError(
                ErrorCode.INVALID_MIME,
                "multipart/related contained a duplicate security-critical parameter",
            )

    for part in message.walk():
        if part.defects:
            raise MhtmlGatewayError(
                ErrorCode.INVALID_MIME,
                "MIME structure contained a parser defect",
            )
        for header_name in _CRITICAL_SINGLETON_HEADERS:
            header_values = part.get_all(header_name, [])
            if len(header_values) > 1:
                raise MhtmlGatewayError(
                    ErrorCode.INVALID_MIME,
                    "MIME structure contained a duplicate security-critical header",
                )
            # Unknown transfer encodings are an intentional enterprise
            # compatibility lane. Root-selection metadata still has to be
            # syntactically unambiguous.
            if header_name != "Content-Transfer-Encoding" and any(
                getattr(value, "defects", ()) for value in header_values
            ):
                raise MhtmlGatewayError(
                    ErrorCode.INVALID_MIME,
                    "MIME structure contained a defective security-critical header",
                )


def _normalize_content_id(value: str | None) -> str | None:
    """Normalize an optional Content-ID by removing surrounding brackets."""
    if value is None:
        return None
    normalized = value.strip().removeprefix("<").removesuffix(">").strip()
    return normalized or None


def _leaf_parts(message: Message) -> list[Message]:
    """Return every non-multipart MIME part in document order."""
    return [part for part in message.walk() if not part.is_multipart()]


def _body_parts(message: Message) -> list[Message]:
    """Return every body part below the top-level entity in document order."""
    if not message.is_multipart():
        return [message]
    return list(message.walk())[1:]


def _select_html_root(message: Message, parts: list[Message]) -> Message:
    """Select the authoritative HTML root using RFC 2387 semantics."""
    if (
        message.get_content_type().lower() == "text/html"
        and not message.is_multipart()
    ):
        return message
    if message.get_content_type().lower() != "multipart/related":
        raise MhtmlGatewayError(
            ErrorCode.INVALID_MIME,
            "Top-level MIME type must be multipart/related or text/html",
        )

    start = _normalize_content_id(message.get_param("start"))
    if start is not None:
        matches = [
            part
            for part in parts
            if _normalize_content_id(part.get("Content-ID")) == start
        ]
        if not matches:
            raise MhtmlGatewayError(
                ErrorCode.MISSING_HTML_ROOT,
                "Explicit multipart/related start identifier did not resolve to text/html",
            )
        if len(matches) > 1:
            raise MhtmlGatewayError(
                ErrorCode.AMBIGUOUS_HTML_ROOT,
                "Explicit multipart/related start identifier matched multiple body parts",
            )
        root = matches[0]
        if root.is_multipart() or root.get_content_type().lower() != "text/html":
            raise MhtmlGatewayError(
                ErrorCode.MISSING_HTML_ROOT,
                "Explicit multipart/related start identifier did not resolve to text/html",
            )
        return root

    direct_payload = message.get_payload()
    if not isinstance(direct_payload, list) or not direct_payload:
        raise MhtmlGatewayError(
            ErrorCode.MISSING_HTML_ROOT,
            "The default multipart/related root was not text/html",
        )
    root = direct_payload[0]
    if root.is_multipart() or root.get_content_type().lower() != "text/html":
        raise MhtmlGatewayError(
            ErrorCode.MISSING_HTML_ROOT,
            "The default multipart/related root was not text/html",
        )
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
        raise MhtmlGatewayError(
            ErrorCode.INVALID_MIME,
            "multipart/related type parameter did not match the selected root content type",
        )
    return ()


def _raw_payload_bytes(part: Message) -> bytes:
    """Return decoded payload bytes, preserving unknown identity encodings."""
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload
    raise MhtmlGatewayError(
        ErrorCode.HTML_DECODE_FAILED,
        "The selected HTML part did not contain a byte payload",
    )


def _select_charset(part: Message, payload: bytes) -> str:
    """Resolve a declared charset or deterministic BOM/UTF-8 fallback."""
    declared = part.get_content_charset()
    if declared:
        try:
            codecs.lookup(declared)
        except LookupError as exc:
            raise MhtmlGatewayError(
                ErrorCode.UNKNOWN_CHARSET,
                "Declared HTML charset is unknown",
            ) from exc
        return declared
    for prefix, encoding in _BOM_ENCODINGS:
        if payload.startswith(prefix):
            return encoding
    return "utf-8"


def _decode_html(part: Message) -> tuple[str, tuple[Diagnostic, ...]]:
    """Decode selected HTML strictly and record compatibility warnings."""
    payload = _raw_payload_bytes(part)
    charset = _select_charset(part, payload)
    try:
        text = payload.decode(charset, errors="strict")
    except UnicodeDecodeError as exc:
        raise MhtmlGatewayError(
            ErrorCode.HTML_DECODE_FAILED,
            "HTML payload did not match the declared or detected charset",
        ) from exc

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
        raise MhtmlGatewayError(ErrorCode.INVALID_MIME, "Source must be bytes")
    if len(source_bytes) > effective_limits.max_source_bytes:
        raise MhtmlGatewayError(
            ErrorCode.SOURCE_TOO_LARGE,
            f"Source contains {len(source_bytes)} bytes; limit is {effective_limits.max_source_bytes}",
        )

    message = BytesParser(policy=policy.default).parsebytes(source_bytes)
    _validate_mime_structure(message)

    leaf_parts = _leaf_parts(message)
    if len(leaf_parts) > effective_limits.max_mime_parts:
        raise MhtmlGatewayError(
            ErrorCode.TOO_MANY_MIME_PARTS,
            f"MIME message contains {len(leaf_parts)} leaf parts; limit is {effective_limits.max_mime_parts}",
        )

    root = _select_html_root(message, _body_parts(message))
    related_diagnostics = _related_type_diagnostics(message, root)
    html_text, decoding_diagnostics = _decode_html(root)
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
        raise MhtmlGatewayError(
            ErrorCode.SOURCE_READ_FAILED,
            "Could not read MHTML source",
        ) from exc
    return parse_mhtml_bytes(source_bytes, limits=limits)
