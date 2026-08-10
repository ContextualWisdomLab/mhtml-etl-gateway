"""Infer PostgreSQL column types and multiword snake_case object names."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence


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
    """Map headers to unique snake_case names (suffix _2, _3, ... on collision)."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for h in headers:
        base = to_snake_case(h)
        n = seen.get(base, 0) + 1
        seen[base] = n
        out.append(base if n == 1 else f"{base}_{n}"[:63])
    return out


def _is_bool(v: str) -> bool:
    return v.strip().lower() in {"true", "false", "t", "f", "yes", "no", "y", "n", "1", "0"} and v.strip().lower() in {
        "true",
        "false",
        "t",
        "f",
        "yes",
        "no",
        "y",
        "n",
    }


def _is_int(v: str) -> bool:
    s = v.strip().replace(",", "")
    if not s or s in {"+", "-"}:
        return False
    if s[0] in "+-":
        s = s[1:]
    return s.isdigit()


def _is_numeric(v: str) -> bool:
    s = v.strip().replace(",", "")
    if not s:
        return False
    try:
        Decimal(s)
        return True
    except (InvalidOperation, ValueError):
        return False


def _is_date(v: str) -> bool:
    s = v.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d.%m.%Y"):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_time(v: str) -> bool:
    s = v.strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S"):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_timestamp(v: str) -> bool:
    s = v.strip()
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


@dataclass(frozen=True)
class TableSchema:
    table_name: str
    columns: list[ColumnSpec]

    def ddl(self, *, include_lineage: bool = True) -> str:
        """Emit CREATE TABLE DDL with optional lineage columns."""
        cols = [f'    "{c.db_name}" {c.pg_type}' for c in self.columns]
        if include_lineage:
            cols.extend(
                [
                    '    "source_artifact_path" TEXT NOT NULL',
                    '    "source_artifact_sha256" TEXT NOT NULL',
                    '    "source_row_number" BIGINT NOT NULL',
                    '    "loaded_at" TIMESTAMP NOT NULL DEFAULT NOW()',
                ]
            )
        body = ",\n".join(cols)
        return f'CREATE TABLE IF NOT EXISTS "{self.table_name}" (\n{body}\n);'

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
        if s.lower() in {"true", "t", "yes", "y", "1", "false", "f", "no", "n", "0"}:
            return s.lower() in {"true", "t", "yes", "y", "1"}
        return s
    if pg_type == PG_BIGINT:
        try:
            return int(s.replace(",", ""))
        except ValueError:
            return s
    if pg_type == PG_NUMERIC:
        try:
            return Decimal(s.replace(",", ""))
        except (InvalidOperation, ValueError):
            return s
    if pg_type == PG_DATE:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return s
    if pg_type == PG_TIME:
        for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S"):
            try:
                return datetime.strptime(s, fmt).time()
            except ValueError:
                continue
        return s
    if pg_type == PG_TIMESTAMP:
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
