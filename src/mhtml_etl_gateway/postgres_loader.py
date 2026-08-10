"""PostgreSQL loader with lineage columns and injectable sink for tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence

from mhtml_etl_gateway.schema_inference import (
    TableSchema,
    coerce_value,
)


class LoadError(ValueError):
    """Fail-closed load error."""


@dataclass
class LoadResult:
    table_name: str
    inserted_rows: int
    ddl: str
    lineage: dict[str, Any] = field(default_factory=dict)


class RowSink(Protocol):
    def ensure_table(self, schema: TableSchema) -> None: ...

    def insert_rows(
        self,
        schema: TableSchema,
        rows: Sequence[Sequence[Any]],
        *,
        source_artifact_path: str,
        source_artifact_sha256: str,
        start_row_number: int = 1,
    ) -> int: ...


class InMemorySink:
    """Injectable sink for unit tests (no live database)."""

    def __init__(self) -> None:
        self.schemas: dict[str, TableSchema] = {}
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self.ddl_statements: list[str] = []

    def ensure_table(self, schema: TableSchema) -> None:
        self.schemas[schema.table_name] = schema
        self.ddl_statements.append(schema.ddl(include_lineage=True))
        self.rows.setdefault(schema.table_name, [])

    def insert_rows(
        self,
        schema: TableSchema,
        rows: Sequence[Sequence[Any]],
        *,
        source_artifact_path: str,
        source_artifact_sha256: str,
        start_row_number: int = 1,
    ) -> int:
        if schema.table_name not in self.schemas:
            raise LoadError(f"table not ensured: {schema.table_name}")
        store = self.rows[schema.table_name]
        loaded_at = datetime.now(timezone.utc)
        for offset, row in enumerate(rows):
            record: dict[str, Any] = {}
            for i, col in enumerate(schema.columns):
                record[col.db_name] = row[i] if i < len(row) else None
            record["source_artifact_path"] = source_artifact_path
            record["source_artifact_sha256"] = source_artifact_sha256
            record["source_row_number"] = start_row_number + offset
            record["loaded_at"] = loaded_at
            store.append(record)
        return len(rows)


class PsycopgSink:
    """Live PostgreSQL sink using psycopg3."""

    def __init__(self, conninfo: str) -> None:
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover
            raise LoadError("psycopg is required for PostgreSQL loading") from exc
        self._psycopg = psycopg
        self._conninfo = conninfo
        self._conn = psycopg.connect(conninfo)
        self._conn.autocommit = False

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PsycopgSink":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def ensure_table(self, schema: TableSchema) -> None:
        ddl = schema.ddl(include_lineage=True)
        with self._conn.cursor() as cur:
            cur.execute(ddl)
        self._conn.commit()

    def insert_rows(
        self,
        schema: TableSchema,
        rows: Sequence[Sequence[Any]],
        *,
        source_artifact_path: str,
        source_artifact_sha256: str,
        start_row_number: int = 1,
    ) -> int:
        if not rows:
            return 0
        col_names = [c.db_name for c in schema.columns] + [
            "source_artifact_path",
            "source_artifact_sha256",
            "source_row_number",
        ]
        placeholders = ", ".join(["%s"] * len(col_names))
        quoted = ", ".join(f'"{n}"' for n in col_names)
        sql = f'INSERT INTO "{schema.table_name}" ({quoted}) VALUES ({placeholders})'
        payloads: list[tuple[Any, ...]] = []
        for offset, row in enumerate(rows):
            values: list[Any] = []
            for i, col in enumerate(schema.columns):
                raw = row[i] if i < len(row) else None
                if isinstance(raw, str):
                    values.append(coerce_value(raw, col.pg_type))
                else:
                    values.append(raw)
            values.extend(
                [
                    source_artifact_path,
                    source_artifact_sha256,
                    start_row_number + offset,
                ]
            )
            payloads.append(tuple(values))
        with self._conn.cursor() as cur:
            cur.executemany(sql, payloads)
        self._conn.commit()
        return len(payloads)

    def query_count(self, table_name: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def query_sample(self, table_name: str, limit: int = 5) -> list[tuple]:
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT * FROM "{table_name}" LIMIT %s', (limit,))
            return list(cur.fetchall())


def prepare_typed_rows(schema: TableSchema, rows: Sequence[Sequence[str]]) -> list[list[Any]]:
    """Coerce string rows to Python types according to schema."""
    prepared: list[list[Any]] = []
    for row in rows:
        prepared.append(
            [
                coerce_value(str(row[i]) if i < len(row) else "", col.pg_type)
                for i, col in enumerate(schema.columns)
            ]
        )
    return prepared


def load_table(
    schema: TableSchema,
    rows: Sequence[Sequence[str]],
    *,
    sink: RowSink,
    source_artifact_path: str,
    source_artifact_sha256: str,
) -> LoadResult:
    """Ensure table and insert rows with lineage metadata."""
    if not schema.columns:
        raise LoadError("schema has no columns")
    sink.ensure_table(schema)
    typed = prepare_typed_rows(schema, rows)
    n = sink.insert_rows(
        schema,
        typed,
        source_artifact_path=source_artifact_path,
        source_artifact_sha256=source_artifact_sha256,
        start_row_number=1,
    )
    return LoadResult(
        table_name=schema.table_name,
        inserted_rows=n,
        ddl=schema.ddl(include_lineage=True),
        lineage={
            "source_artifact_path": source_artifact_path,
            "source_artifact_sha256": source_artifact_sha256,
            "inserted_rows": n,
            "table_name": schema.table_name,
        },
    )
