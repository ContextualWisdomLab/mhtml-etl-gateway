"""Load column mapping references and attach PostgreSQL column comments.

The gateway accepts explicit JSON/CSV mappings and the text layer of a PPTX
mapping deck.  A mapping reference is deliberately treated as metadata: fields
that are not present in the current MHTML table are reported as unmatched, and
ambiguous or conflicting mappings fail closed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from defusedxml import ElementTree

from mhtml_etl_gateway.lineage import artifact_reference
from mhtml_etl_gateway.schema_inference import TableSchema, to_snake_case


class ColumnMappingError(ValueError):
    """Fail-closed mapping document or resolution error."""


@dataclass(frozen=True)
class ColumnMapping:
    """One source-field to target-column description mapping."""

    source_name: str
    comment: str
    target_name: str | None = None
    context: str | None = None
    slide_number: int | None = None


@dataclass(frozen=True)
class ColumnMappingDocument:
    """Parsed mapping document with an opaque artifact reference."""

    path: str
    format: str
    mappings: tuple[ColumnMapping, ...]


@dataclass(frozen=True)
class ColumnMappingReport:
    """Resolution evidence returned with a pipeline result."""

    path: str
    format: str
    matched: dict[str, str]
    unmatched: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return privacy-safe mapping resolution evidence for JSON output."""
        return {
            "path": self.path,
            "format": self.format,
            "matched_count": len(self.matched),
            "matched": dict(self.matched),
            "unmatched_count": len(self.unmatched),
            "unmatched": list(self.unmatched),
        }


_SOURCE_KEYS = (
    "source",
    "source_name",
    "source_column",
    "source_field",
    "field",
    "column",
)
_TARGET_KEYS = ("target", "target_name", "target_column", "db_name", "postgres_column")
_COMMENT_KEYS = (
    "comment",
    "description",
    "label",
    "meaning",
    "display_name",
)
_CONTEXT_KEYS = ("context", "screen", "section", "subject")
_QUALIFIED_FIELD = re.compile(
    r"(?P<table>[A-Z][A-Z0-9_]*)\s*\.\s*(?P<field>[A-Z][A-Z0-9_]*)",
    re.IGNORECASE,
)
_SECTION_TITLE = re.compile(r"^\s*(?P<number>\d+)\.\s*(?P<title>.+?)\s*$")
_SLIDE_NUMBER = re.compile(r"ppt/slides/slide(?P<number>\d+)\.xml$")


def _mapping_reference(path: Path) -> str:
    """Return an opaque reference derived from mapping content, never its path."""
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise ColumnMappingError("cannot fingerprint column mapping artifact") from None
    return artifact_reference(digest)


def _key_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _first_value(record: Mapping[str, Any], aliases: Sequence[str]) -> Any:
    normalized = {_key_name(key): value for key, value in record.items()}
    for alias in aliases:
        value = normalized.get(_key_name(alias))
        if value is not None and str(value).strip() != "":
            return value
    return None


def _normalise_source(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"\s*\.\s*", ".", text)
    text = re.sub(r"\s+", " ", text)
    if not text:
        raise ColumnMappingError("mapping source name is empty")
    return text


def _mapping_from_record(record: Mapping[str, Any], *, location: str) -> ColumnMapping:
    source = _first_value(record, _SOURCE_KEYS)
    if source is None:
        raise ColumnMappingError(f"{location}: missing source column")
    comment = _first_value(record, _COMMENT_KEYS)
    if comment is None:
        raise ColumnMappingError(f"{location}: missing comment/description")
    comment_text = str(comment).strip()
    if not comment_text:
        raise ColumnMappingError(f"{location}: empty comment")
    target = _first_value(record, _TARGET_KEYS)
    context = _first_value(record, _CONTEXT_KEYS)
    return ColumnMapping(
        source_name=_normalise_source(source),
        comment=comment_text,
        target_name=str(target).strip() if target is not None else None,
        context=str(context).strip() if context is not None else None,
    )


def _dedupe_mappings(mappings: Iterable[ColumnMapping]) -> tuple[ColumnMapping, ...]:
    seen: set[tuple[str, str, str | None]] = set()
    out: list[ColumnMapping] = []
    for mapping in mappings:
        key = (mapping.source_name.casefold(), mapping.comment, mapping.target_name)
        if key not in seen:
            seen.add(key)
            out.append(mapping)
    return tuple(out)


def _json_records(data: Any) -> list[Mapping[str, Any]]:
    if isinstance(data, list):
        if not all(isinstance(item, Mapping) for item in data):
            raise ColumnMappingError("JSON mapping records must be objects")
        return list(data)
    if not isinstance(data, Mapping):
        raise ColumnMappingError("JSON mapping must be an object or array")

    for key in ("columns", "mappings", "column_mappings"):
        if key in data:
            records = data[key]
            if not isinstance(records, list) or not all(
                isinstance(item, Mapping) for item in records
            ):
                raise ColumnMappingError(
                    f"JSON mapping {key!r} must be an array of objects"
                )
            return list(records)

    normalized_keys = {_key_name(key) for key in data}
    if normalized_keys.intersection(
        {_key_name(key) for key in (*_SOURCE_KEYS, *_COMMENT_KEYS)}
    ):
        return [data]

    # Compact form: {"SOURCE.FIELD": "human-readable comment"}.
    records: list[Mapping[str, Any]] = []
    for source, value in data.items():
        if isinstance(value, Mapping):
            record = dict(value)
            record.setdefault("source", source)
        else:
            record = {"source": source, "comment": value}
        records.append(record)
    return records


def _load_json(path: Path) -> tuple[ColumnMapping, ...]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ColumnMappingError("cannot read JSON mapping") from None
    records = _json_records(data)
    mappings = [
        _mapping_from_record(record, location=f"JSON mapping record {index}")
        for index, record in enumerate(records, 1)
    ]
    if not mappings:
        raise ColumnMappingError("JSON mapping has no mapping records")
    return _dedupe_mappings(mappings)


def _load_csv(path: Path) -> tuple[ColumnMapping, ...]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ColumnMappingError("CSV mapping has no header row")
            mappings = [
                _mapping_from_record(row, location=f"CSV mapping row {reader.line_num}")
                for row in reader
                if any(str(value or "").strip() for value in row.values())
            ]
    except ColumnMappingError:
        raise
    except (OSError, UnicodeError, csv.Error):
        raise ColumnMappingError("cannot read CSV mapping") from None
    if not mappings:
        raise ColumnMappingError("CSV mapping has no mapping records")
    return _dedupe_mappings(mappings)


def _xml_texts(raw_xml: bytes) -> list[str]:
    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError as exc:
        raise ColumnMappingError(
            f"invalid PPTX slide XML: {type(exc).__name__}"
        ) from None
    texts: list[str] = []
    paragraphs = [
        element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "p"
    ]
    for paragraph in paragraphs:
        value = "".join(
            element.text or ""
            for element in paragraph.iter()
            if element.tag.rsplit("}", 1)[-1] == "t"
        ).strip()
        if value:
            texts.append(value)
    if texts:
        return texts
    # Keep a defensive fallback for unusual PPTX producers that omit the
    # expected paragraph nodes.
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "t" and element.text:
            text = element.text.strip()
            if text:
                texts.append(text)
    return texts


def _slide_sources(text: str) -> list[str]:
    matches = list(_QUALIFIED_FIELD.finditer(text))
    sources: list[str] = []
    for index, match in enumerate(matches):
        table = match.group("table").upper()
        field = match.group("field").upper()
        sources.append(f"{table}.{field}")

        # The deck uses expressions such as ``TABLE.ERDAT / ERZET`` and
        # ``TABLE.ERDAT + APV_TIME``.  Carry the qualified table across those
        # separators, while ignoring a bare table reference such as ZCRHT001.
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        tail = text[match.end() : end]
        for extra in re.finditer(r"(?:[+/,&]\s*)([A-Z][A-Z0-9_]*)", tail, re.I):
            extra_field = extra.group(1).upper()
            if re.fullmatch(r"ZCRHT\d+", extra_field, re.I):
                continue
            sources.append(f"{table}.{extra_field}")
    return sources


def _load_pptx(path: Path) -> tuple[ColumnMapping, ...]:
    contexts: dict[str, list[tuple[int, str]]] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            slide_files: list[tuple[int, str]] = []
            for name in archive.namelist():
                match = _SLIDE_NUMBER.fullmatch(name)
                if match:
                    slide_files.append((int(match.group("number")), name))
            if not slide_files:
                raise ColumnMappingError("PPTX has no slides")
            for slide_number, name in sorted(slide_files):
                texts = _xml_texts(archive.read(name))
                section = next(
                    (
                        f"{match.group('number')}. {match.group('title')}"
                        for text in texts
                        if (match := _SECTION_TITLE.match(text))
                    ),
                    "VOC column mapping",
                )
                slide_context = f"{section} (slide {slide_number})"
                for text in texts:
                    for source in _slide_sources(text):
                        values = contexts.setdefault(source, [])
                        context_entry = (slide_number, slide_context)
                        if context_entry not in values:
                            values.append(context_entry)
    except ColumnMappingError:
        raise
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise ColumnMappingError(
            f"cannot read PPTX mapping: {type(exc).__name__}"
        ) from None

    mappings = [
        ColumnMapping(
            source_name=source,
            comment=f"VOC mapping: {slide_context} — {source}",
            context=slide_context,
            slide_number=slide_number,
        )
        for source, slide_contexts in contexts.items()
        for slide_number, slide_context in slide_contexts
    ]
    if not mappings:
        raise ColumnMappingError("PPTX text layer has no qualified source fields")
    return _dedupe_mappings(mappings)


def load_column_mapping(path: str | Path) -> ColumnMappingDocument:
    """Load a JSON, CSV, or PPTX column mapping reference."""
    mapping_path = Path(path)
    if not mapping_path.is_file():
        raise ColumnMappingError("column mapping file not found")
    suffix = mapping_path.suffix.lower()
    if suffix == ".json":
        mappings = _load_json(mapping_path)
        format_name = "json"
    elif suffix == ".csv":
        mappings = _load_csv(mapping_path)
        format_name = "csv"
    elif suffix == ".pptx":
        mappings = _load_pptx(mapping_path)
        format_name = "pptx"
    else:
        raise ColumnMappingError(
            f"unsupported column mapping format {mapping_path.suffix!r}; use .json, .csv, or .pptx"
        )
    return ColumnMappingDocument(
        path=_mapping_reference(mapping_path),
        format=format_name,
        mappings=mappings,
    )


def _source_candidates(schema: TableSchema, source_name: str) -> list[str]:
    source_key = source_name.casefold()
    source_suffix = source_name.rsplit(".", 1)[-1].casefold()
    candidates: list[str] = []
    for column in schema.columns:
        column_source = column.source_name.strip().casefold()
        column_suffix = column.source_name.rsplit(".", 1)[-1].strip().casefold()
        if column_source == source_key or column_suffix == source_suffix:
            candidates.append(column.db_name)
            continue
        if "." not in source_name and column.db_name.casefold() == source_key:
            candidates.append(column.db_name)
            continue
        try:
            if to_snake_case(source_suffix) == column.db_name.casefold():
                candidates.append(column.db_name)
        except ValueError:
            # Ignore malformed mapping text and continue checking other candidates.
            pass
    return candidates


def _target_candidates(schema: TableSchema, target_name: str) -> list[str]:
    target_key = target_name.strip().casefold()
    candidates = [
        column.db_name
        for column in schema.columns
        if column.db_name.casefold() == target_key
    ]
    if candidates:
        return candidates
    try:
        normalized = to_snake_case(target_name).casefold()
    except ValueError:
        return []
    return [
        column.db_name
        for column in schema.columns
        if column.db_name.casefold() == normalized
    ]


def attach_column_comments(
    schema: TableSchema,
    document: ColumnMappingDocument,
) -> tuple[TableSchema, ColumnMappingReport]:
    """Resolve mappings against a schema and return a commented schema/report."""
    comments: dict[str, str] = {}
    matched: dict[str, str] = {}
    unmatched: list[str] = []
    for mapping in document.mappings:
        candidates = (
            _target_candidates(schema, mapping.target_name)
            if mapping.target_name
            else _source_candidates(schema, mapping.source_name)
        )
        if not candidates:
            if mapping.source_name not in unmatched:
                unmatched.append(mapping.source_name)
            continue
        if len(candidates) > 1:
            raise ColumnMappingError(
                f"ambiguous mapping {mapping.source_name!r}: matches {', '.join(candidates)}"
            )
        db_name = candidates[0]
        previous = comments.get(db_name)
        if previous is not None and previous != mapping.comment:
            if document.format == "pptx":
                # A deck can show the same SAP field suffix (for example
                # ERDAT) from several source tables.  The extracted MHTML
                # header may contain only that suffix, so retain all source
                # contexts in one deterministic comment.
                comments[db_name] = f"{previous}; {mapping.comment}"
            else:
                raise ColumnMappingError(
                    f"conflicting comments for {db_name!r}: {previous!r} vs {mapping.comment!r}"
                )
        else:
            comments[db_name] = mapping.comment
        matched[mapping.source_name] = db_name

    commented_schema = schema.with_column_comments(comments)
    report = ColumnMappingReport(
        path=document.path,
        format=document.format,
        matched=matched,
        unmatched=tuple(unmatched),
    )
    return commented_schema, report
