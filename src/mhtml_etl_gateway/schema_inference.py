"""Infer PostgreSQL column types and multiword snake_case object names."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Sequence


# PostgreSQL type names used by the gateway.
PG_TEXT = "TEXT"
PG_BOOLEAN = "BOOLEAN"
PG_BIGINT = "BIGINT"
PG_NUMERIC = "NUMERIC"
PG_DATE = "DATE"
PG_TIME = "TIME"
PG_TIMESTAMP = "TIMESTAMP"


class SchemaInferenceError(ValueError):
    """Fail-closed schema inference error."""


_NON_ALNUM = re.compile(r"[^0-9a-zA-Z]+")
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def to_snake_case(name: str) -> str:
    """Convert a header/identifier to multiword snake_case for PostgreSQL."""
    if name is None:
        raise SchemaInferenceError("column name is None")
    s = str(name).strip()
    if not s:
        raise SchemaInferenceError("empty column name")
    s = _CAMEL_BOUNDARY.sub(r"\1_\2", s)
    s = _NON_ALNUM.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("_").lower()
    if not s:
        raise SchemaInferenceError(f"column name collapses to empty: {name!r}")
    if s[0].isdigit():
        s = f"col_{s}"
    # PostgreSQL identifier length safety.
    return s[:63]


def unique_snake_names(headers: Sequence[str]) -> list[str]:
    """Map headers to unique snake_case names (suffix _2, _3, ... on collision).

    Re-checks truncated candidates so ["A", "A_2", "A"] and 63-char cuts stay unique.
    """
    used: set[str] = set()
    out: list[str] = []
    for h in headers:
        base = to_snake_case(h)
        candidate = base[:63]
        n = 1
        while candidate in used:
            n += 1
            suffix = f"_{n}"
            candidate = f"{base[: 63 - len(suffix)]}{suffix}"
        used.add(candidate)
        out.append(candidate)
    return out


_BOOL_LITERALS = frozenset({"true", "false", "t", "f", "yes", "no", "y", "n"})


def _is_bool(v: str) -> bool:
    return v.strip().lower() in _BOOL_LITERALS


def _parse_int(v: str) -> int | None:
    """Shared int parse for inference and coerce (thousand separators allowed)."""
    s = v.strip()
    if not s or s in {"+", "-"}:
        return None
    # Allow 1,234 style thousands only (not arbitrary commas).
    if "," in s:
        if not re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+", s):
            return None
        s = s.replace(",", "")
    if s[0] in "+-":
        body = s[1:]
    else:
        body = s
    if not body.isdigit():
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_decimal(v: str) -> Decimal | None:
    s = v.strip()
    if not s:
        return None
    # Reject malformed thousand groupings (e.g. "12,34", "1,23,456").
    if "," in s:
        if not re.fullmatch(r"[+-]?\d{1,3}(,\d{3})*(\.\d+)?", s):
            return None
        s = s.replace(",", "")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _is_int(v: str) -> bool:
    return _parse_int(v) is not None


def _is_numeric(v: str) -> bool:
    return _parse_decimal(v) is not None


def _is_date(v: str) -> bool:
    s = v.strip()
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d.%m.%Y"):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_time(v: str) -> bool:
    s = v.strip()
    try:
        time.fromisoformat(s)
        return True
    except ValueError:
        pass
    for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S"):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_timestamp(v: str) -> bool:
    s = v.strip()
    try:
        # datetime.fromisoformat() parses '2026-02-20' without a time part successfully.
        # But for _is_timestamp, we specifically want to require a time part if relying on fromisoformat,
        # or we check if there's a space or 'T' indicating time.
        if " " in s or "T" in s or "t" in s:
            parsed = datetime.fromisoformat(s)
            # TIMESTAMP is without time zone; preserve offset-bearing values as TEXT.
            if parsed.tzinfo is not None:
                return False
            return True
    except ValueError:
        # ISO-like inputs can still match one of the legacy formats below.
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


def _nonempty(values: Iterable[str]) -> list[str]:
    return [v for v in values if v is not None and str(v).strip() != ""]


def infer_pg_type(samples: Sequence[str]) -> str:
    """Infer a single PostgreSQL type from sample cell strings."""
    vals = _nonempty(samples)
    if not vals:
        return PG_TEXT
    if all(_is_bool(v) for v in vals):
        return PG_BOOLEAN
    if all(_is_int(v) for v in vals):
        return PG_BIGINT
    if all(_is_numeric(v) for v in vals):
        return PG_NUMERIC
    if all(_is_timestamp(v) for v in vals):
        return PG_TIMESTAMP
    if all(_is_date(v) for v in vals):
        return PG_DATE
    if all(_is_time(v) for v in vals):
        return PG_TIME
    return PG_TEXT


@dataclass(frozen=True)
class ColumnSpec:
    source_name: str
    db_name: str
    pg_type: str
    comment: str | None = None


@dataclass(frozen=True)
class TableSchema:
    table_name: str
    columns: list[ColumnSpec]

    def create_ddl(self, *, include_lineage: bool = True) -> str:
        """Emit CREATE TABLE DDL with optional lineage columns.

        Identifiers are restricted to validated snake_case (see sql_ident).
        """
        from mhtml_etl_gateway.sql_ident import require_safe_ident

        table = require_safe_ident(self.table_name)
        cols: list[str] = []
        for c in self.columns:
            col = require_safe_ident(c.db_name)
            # pg_type is from a fixed allow-list in this package.
            cols.append(f"    {col} {c.pg_type}")
        if include_lineage:
            cols.extend(
                [
                    "    source_artifact_path TEXT NOT NULL",
                    "    source_artifact_sha256 TEXT NOT NULL",
                    "    source_row_number BIGINT NOT NULL",
                    "    loaded_at TIMESTAMP NOT NULL DEFAULT NOW()",
                ]
            )
        body = ",\n".join(cols)
        return f"CREATE TABLE IF NOT EXISTS {table} (\n{body}\n);"

    def comment_ddl(self) -> list[str]:
        """Emit COMMENT ON statements for mapped business columns."""
        from mhtml_etl_gateway.sql_ident import quote_sql_literal, require_safe_ident

        table = require_safe_ident(self.table_name)
        statements: list[str] = []
        for column in self.columns:
            if column.comment is None:
                continue
            name = require_safe_ident(column.db_name)
            statements.append(
                f"COMMENT ON COLUMN {table}.{name} IS {quote_sql_literal(column.comment)};"
            )
        return statements

    def ddl(
        self,
        *,
        include_lineage: bool = True,
        include_comments: bool = True,
    ) -> str:
        """Emit CREATE TABLE DDL followed by mapped COMMENT ON statements."""
        statements = [self.create_ddl(include_lineage=include_lineage)]
        if include_comments:
            statements.extend(self.comment_ddl())
        return "\n\n".join(statements)

    def with_column_comments(self, comments: Mapping[str, str]) -> "TableSchema":
        """Return a schema with comments attached by database column name."""
        return replace(
            self,
            columns=[
                replace(column, comment=comments.get(column.db_name, column.comment))
                for column in self.columns
            ],
        )

    def comment_map(self) -> dict[str, str]:
        """Return applied comments keyed by database column name."""
        return {
            column.db_name: column.comment
            for column in self.columns
            if column.comment is not None
        }

    def type_map(self) -> dict[str, str]:
        return {c.source_name: c.pg_type for c in self.columns}


def infer_table_schema(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    table_name: str = "mhtml_extracted_rows",
    sample_limit: int = 200,
) -> TableSchema:
    """Build a TableSchema from headers + row samples."""
    if not headers:
        raise SchemaInferenceError("no headers for schema inference")
    db_names = unique_snake_names(list(headers))
    table = to_snake_case(table_name)
    columns: list[ColumnSpec] = []
    sample_rows = list(rows[:sample_limit])
    for i, src in enumerate(headers):
        samples = [str(r[i]) if i < len(r) else "" for r in sample_rows]
        pg_type = infer_pg_type(samples)
        columns.append(ColumnSpec(source_name=str(src), db_name=db_names[i], pg_type=pg_type))
    return TableSchema(table_name=table, columns=columns)


def coerce_value(value: str, pg_type: str):
    """Coerce a cell string to a Python value suitable for psycopg / PostgreSQL.

    Non-conforming values fall back to the original string (caller/sink may
    promote the column to TEXT for multi-file schema evolution).
    """
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    if pg_type == PG_BOOLEAN:
        low = s.lower()
        if low in _BOOL_LITERALS:
            return low in {"true", "t", "yes", "y"}
        return s
    if pg_type == PG_BIGINT:
        parsed = _parse_int(s)
        return parsed if parsed is not None else s
    if pg_type == PG_NUMERIC:
        parsed = _parse_decimal(s)
        return parsed if parsed is not None else s
    if pg_type == PG_DATE:
        try:
            return date.fromisoformat(s)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return s
    if pg_type == PG_TIME:
        try:
            return time.fromisoformat(s)
        except ValueError:
            pass
        for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S"):
            try:
                return datetime.strptime(s, fmt).time()
            except ValueError:
                continue
        return s
    if pg_type == PG_TIMESTAMP:
        try:
            # We know it's supposed to be a timestamp, so we can try fromisoformat
            if " " in s or "T" in s or "t" in s:
                parsed = datetime.fromisoformat(s)
                # Do not silently discard an explicit offset in TIMESTAMP columns.
                return parsed if parsed.tzinfo is None else s
        except ValueError:
            # Parse failures fall through to the supported legacy timestamp formats.
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return s
    return s


def values_require_text(pg_type: str, values: Sequence[object]) -> bool:
    """True when typed column cannot hold one of the prepared values."""
    if pg_type == PG_TEXT:
        return False
    for v in values:
        if v is None:
            continue
        if pg_type == PG_BIGINT and not isinstance(v, int):
            return True
        if pg_type == PG_NUMERIC and not isinstance(v, (int, Decimal, float)):
            return True
        if pg_type == PG_BOOLEAN and not isinstance(v, bool):
            return True
        if pg_type == PG_DATE and not isinstance(v, date):
            return True
        if pg_type == PG_TIME and not isinstance(v, time):
            return True
        if pg_type == PG_TIMESTAMP and not isinstance(v, datetime):
            return True
    return False
