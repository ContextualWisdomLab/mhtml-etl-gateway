"""Owner-issued, value-free receipts for deterministic MHTML table extraction.

The receipt commits to exact source and output content identities plus the
released extractor contract/configuration. It deliberately does not contain
protected headers or row values and does not authenticate a receipt parsed from
external JSON; callers that need trusted replay must restore it through an
owner-authenticated repository or service boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
import secrets
import time
from pathlib import Path
from typing import Sequence
from uuid import RFC_4122, UUID

from .pipeline import extract_table


EXTRACTION_RECEIPT_SCHEMA_VERSION = "mhtml_etl_gateway.extraction_receipt.v1"
"""Canonical wire-schema identity for extraction receipts."""

EXTRACTION_RECEIPT_WIRE_BYTE_LIMIT = 8 * 1024
"""Maximum UTF-8 bytes accepted from an already-decoded JSON string before parsing."""

_EXTRACTION_CONTRACT = "mhtml_etl_gateway.extract_table@1"
_IMPLEMENTATION_RELEASE = "v0.4.0@779254927abb1e7cee80fd949907ccd03f9fc7be"
_OUTPUT_KIND = "table"
_OUTPUT_NORMALIZATION = "headers_rows_canonical_json_v1"
_SAFE_COMPONENT = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}\Z")
_CONCRETE_COMPONENT = re.compile(r"mime-part:[0-9]+\.table:[0-9]+\Z")
_IMMUTABLE_RELEASE = re.compile(
    r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?@[0-9a-f]{40}\Z"
)
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONFIGURATION_PROFILE = {
    "blank_data_rows": "drop",
    "colspan": "expand_max_100000",
    "empty_header": "col_1_based",
    "html_decode": "declared_charset_else_bom_else_utf8_strict",
    "html_part_selection": "rfc2387_start_else_first_direct_html",
    "mime_part_identity": "bounded_body_entity_document_order_v1",
    "nested_tables": "top_level_with_nested_text",
    "ragged_rows": "preserve",
    "table_selection": "largest_columns_x_max_rows_1",
}
_CONFIGURATION_SHA256 = hashlib.sha256(
    json.dumps(
        _CONFIGURATION_PROFILE,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
).hexdigest()
_RECEIPT_FIELD_NAMES = (
    "schema_version",
    "receipt_id",
    "source_artifact_ref",
    "source_sha256",
    "source_size_bytes",
    "output_sha256",
    "output_kind",
    "output_normalization",
    "extraction_contract",
    "implementation_release",
    "configuration_sha256",
    "selected_component",
)
_RECEIPT_FIELDS = frozenset(_RECEIPT_FIELD_NAMES)


def _require(condition: bool) -> None:
    """Fail closed without leaking which untrusted receipt field was invalid."""
    if not condition:
        raise ValueError("invalid extraction receipt")


def _new_uuid7() -> str:
    """Mint an RFC 9562 UUIDv7 using only the Python 3.11 standard library."""
    unix_ms = time.time_ns() // 1_000_000
    random_a = secrets.randbits(12)
    random_b = secrets.randbits(62)
    value = (
        (unix_ms << 80)
        | (0x7 << 76)
        | (random_a << 64)
        | (0b10 << 62)
        | random_b
    )
    return str(UUID(int=value))


def _output_sha256(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> str:
    """Hash the protected canonical output representation without returning it."""
    canonical = json.dumps(
        {"headers": list(headers), "rows": [list(row) for row in rows]},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize the value-free receipt mapping deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _validate_structural_payload(payload: dict[str, object]) -> None:
    """Validate wire structure and immutable-locator syntax without authenticating issuance."""
    _require(set(payload) == _RECEIPT_FIELDS)
    _require(payload["schema_version"] == EXTRACTION_RECEIPT_SCHEMA_VERSION)

    receipt_id = payload["receipt_id"]
    _require(type(receipt_id) is str)
    parsed_id = UUID(receipt_id)
    _require(str(parsed_id) == receipt_id and parsed_id.version == 7 and parsed_id.variant == RFC_4122)

    source_sha256 = payload["source_sha256"]
    output_sha256 = payload["output_sha256"]
    configuration_sha256 = payload["configuration_sha256"]
    _require(type(source_sha256) is str and _LOWER_SHA256.fullmatch(source_sha256) is not None)
    _require(type(output_sha256) is str and _LOWER_SHA256.fullmatch(output_sha256) is not None)
    _require(
        type(configuration_sha256) is str
        and _LOWER_SHA256.fullmatch(configuration_sha256) is not None
    )

    source_artifact_ref = payload["source_artifact_ref"]
    _require(
        type(source_artifact_ref) is str
        and source_artifact_ref == f"artifact:{source_sha256[:16]}"
    )
    source_size_bytes = payload["source_size_bytes"]
    _require(type(source_size_bytes) is int and source_size_bytes >= 0)

    _require(payload["output_kind"] == _OUTPUT_KIND)
    _require(payload["output_normalization"] == _OUTPUT_NORMALIZATION)
    _require(payload["extraction_contract"] == _EXTRACTION_CONTRACT)

    implementation_release = payload["implementation_release"]
    _require(
        type(implementation_release) is str
        and _IMMUTABLE_RELEASE.fullmatch(implementation_release) is not None
    )
    selected_component = payload["selected_component"]
    _require(
        type(selected_component) is str
        and _SAFE_COMPONENT.fullmatch(selected_component) is not None
    )


def _validate_owner_payload(payload: dict[str, object]) -> None:
    """Require the exact static authority tuple and concrete selection shape this owner mints."""
    _validate_structural_payload(payload)
    _require(payload["implementation_release"] == _IMPLEMENTATION_RELEASE)
    _require(payload["configuration_sha256"] == _CONFIGURATION_SHA256)
    selected_component = payload["selected_component"]
    _require(
        type(selected_component) is str
        and _CONCRETE_COMPONENT.fullmatch(selected_component) is not None
    )


def _validate_wire_byte_limit(wire: object) -> str:
    """Bound UTF-8 work before JSON parsing while acknowledging caller-owned string allocation."""
    _require(type(wire) is str)
    typed_wire = wire
    _require(len(typed_wire) <= EXTRACTION_RECEIPT_WIRE_BYTE_LIMIT)
    try:
        utf8_length = len(typed_wire.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("invalid extraction receipt") from exc
    _require(utf8_length <= EXTRACTION_RECEIPT_WIRE_BYTE_LIMIT)
    return typed_wire


def _populate_frozen_record(instance: object, payload: dict[str, object]) -> None:
    """Populate one init-disabled frozen owner/wire record inside this module only."""
    for name in _RECEIPT_FIELD_NAMES:
        object.__setattr__(instance, name, payload[name])


def _owner_payload(instance: "ExtractionReceiptV1") -> dict[str, object]:
    """Return only canonical wire fields from an owner receipt, excluding mint state."""
    return {name: getattr(instance, name) for name in _RECEIPT_FIELD_NAMES}


@dataclass(frozen=True, slots=True, init=False)
class ExtractionReceiptV1:
    """Owner-issued value-free receipt for one exact MHTML table extraction.

    The public constructor is disabled. Receipts are minted only by the owner
    extraction function after it executes the transformation and commits its
    exact output digest. Python object privacy is not an authentication boundary;
    persisted/external restoration still belongs to an authenticated owner
    repository or service.
    """

    schema_version: str
    receipt_id: str
    source_artifact_ref: str
    source_sha256: str
    source_size_bytes: int
    output_sha256: str
    output_kind: str
    output_normalization: str
    extraction_contract: str
    implementation_release: str
    configuration_sha256: str
    selected_component: str
    _minted_selected_component: str

    @classmethod
    def _mint(cls, payload: dict[str, object]) -> "ExtractionReceiptV1":
        """Mint a validated owner record for the private owner extraction path."""
        _validate_owner_payload(payload)
        instance = object.__new__(cls)
        _populate_frozen_record(instance, payload)
        object.__setattr__(
            instance,
            "_minted_selected_component",
            payload["selected_component"],
        )
        return instance

    def to_json(self) -> str:
        """Return canonical value-free JSON after rechecking exact owner authority."""
        payload = _owner_payload(self)
        _validate_owner_payload(payload)
        _require(self.selected_component == self._minted_selected_component)
        wire = _canonical_json(payload)
        _require(len(wire.encode("utf-8")) <= EXTRACTION_RECEIPT_WIRE_BYTE_LIMIT)
        return wire

    def binding_sha256(self) -> str:
        """Return the SHA-256 of canonical receipt JSON for opaque downstream binding."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    def matches_output(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
    ) -> bool:
        """Return whether protected output values reproduce this receipt's output digest."""
        return _output_sha256(headers, rows) == self.output_sha256


@dataclass(frozen=True, slots=True, init=False)
class ValidatedExtractionReceiptWireV1:
    """Canonical structurally valid receipt bytes without owner authentication.

    The public constructor is disabled so callers cannot manufacture a value
    already labelled as validated. Use :meth:`from_json` for structural checks;
    the result still does not authenticate owner issuance.
    """

    schema_version: str
    receipt_id: str
    source_artifact_ref: str
    source_sha256: str
    source_size_bytes: int
    output_sha256: str
    output_kind: str
    output_normalization: str
    extraction_contract: str
    implementation_release: str
    configuration_sha256: str
    selected_component: str

    @classmethod
    def from_json(cls, wire: str) -> "ValidatedExtractionReceiptWireV1":
        """Validate bounded canonical JSON without promoting it to owner-issued state."""
        bounded_wire = _validate_wire_byte_limit(wire)
        try:
            payload = json.loads(bounded_wire)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError("invalid extraction receipt") from exc
        _require(type(payload) is dict)
        _validate_structural_payload(payload)
        _require(_canonical_json(payload) == bounded_wire)
        instance = object.__new__(cls)
        _populate_frozen_record(instance, payload)
        return instance

    def binding_sha256(self) -> str:
        """Return the structural receipt binding without claiming owner authentication."""
        return hashlib.sha256(_canonical_json(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, init=False)
class ReceiptBoundExtractResult:
    """Immutable protected extraction output paired by the owner with its receipt."""

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    receipt: ExtractionReceiptV1

    @classmethod
    def _bind(
        cls,
        headers: tuple[str, ...],
        rows: tuple[tuple[str, ...], ...],
        receipt: ExtractionReceiptV1,
    ) -> "ReceiptBoundExtractResult":
        """Create an internally verified output/receipt pair after owner extraction."""
        receipt.to_json()
        _require(receipt.matches_output(headers, rows))
        instance = object.__new__(cls)
        object.__setattr__(instance, "headers", headers)
        object.__setattr__(instance, "rows", rows)
        object.__setattr__(instance, "receipt", receipt)
        return instance


def extract_table_with_receipt(
    path: str | Path,
    *,
    data: bytes | None = None,
) -> ReceiptBoundExtractResult:
    """Execute the real extraction boundary and mint its value-free provenance receipt.

    The function performs extraction itself so callers cannot present an arbitrary
    preconstructed output as owner-derived. Returned headers/rows are frozen after
    the output digest is committed into the receipt.
    """
    extracted = extract_table(path, data=data)
    _require(type(extracted.selected_component) is str)
    headers = tuple(extracted.headers)
    rows = tuple(tuple(row) for row in extracted.rows)
    payload: dict[str, object] = {
        "schema_version": EXTRACTION_RECEIPT_SCHEMA_VERSION,
        "receipt_id": _new_uuid7(),
        "source_artifact_ref": extracted.source_path,
        "source_sha256": extracted.source_sha256,
        "source_size_bytes": extracted.source_size,
        "output_sha256": _output_sha256(headers, rows),
        "output_kind": _OUTPUT_KIND,
        "output_normalization": _OUTPUT_NORMALIZATION,
        "extraction_contract": _EXTRACTION_CONTRACT,
        "implementation_release": _IMPLEMENTATION_RELEASE,
        "configuration_sha256": _CONFIGURATION_SHA256,
        "selected_component": extracted.selected_component,
    }
    receipt = ExtractionReceiptV1._mint(payload)
    return ReceiptBoundExtractResult._bind(headers, rows, receipt)
