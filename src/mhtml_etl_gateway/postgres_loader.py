"""PostgreSQL loader with lineage, ingest catalog, and idempotent loads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol, Sequence

from mhtml_etl_gateway.ingest_catalog import (
    CATALOG_DDL,
    CATALOG_TABLE,
    CatalogEntry,
    make_catalog_entry,
)
from mhtml_etl_gateway.schema_inference import (
    TableSchema,
    coerce_value,
)

OnDuplicate = Literal["skip", "replace"]


class LoadError(ValueError):
    """Fail-closed load error."""


@dataclass
class LoadResult:
    table_name: str
    inserted_rows: int
    ddl: str
    skipped: bool = False
    replaced: bool = False
    catalog_entry: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)


class RowSink(Protocol):
    def ensure_table(self, schema: TableSchema) -> None: ...

    def ensure_catalog(self) -> None: ...

    def catalog_get(self, sha256: str, table_name: str) -> CatalogEntry | None: ...

    def catalog_upsert(self, entry: CatalogEntry) -> None: ...

    def delete_rows_for_artifact(self, table_name: str, sha256: str) -> int: ...

    def count_rows(self, table_name: str) -> int: ...

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
        self.catalog: dict[tuple[str, str], CatalogEntry] = {}

    def ensure_table(self, schema: TableSchema) -> None:
        self.schemas[schema.table_name] = schema
        self.ddl_statements.append(schema.ddl(include_lineage=True))
        self.rows.setdefault(schema.table_name, [])

    def ensure_catalog(self) -> None:
        self.ddl_statements.append(CATALOG_DDL)

    def catalog_get(self, sha256: str, table_name: str) -> CatalogEntry | None:
        return self.catalog.get((sha256, table_name))

    def catalog_upsert(self, entry: CatalogEntry) -> None:
        self.catalog[(entry.source_artifact_sha256, entry.table_name)] = entry

    def delete_rows_for_artifact(self, table_name: str, sha256: str) -> int:
        store = self.rows.get(table_name, [])
        kept = [r for r in store if r.get("source_artifact_sha256") != sha256]
        removed = len(store) - len(kept)
        self.rows[table_name] = kept
        return removed

    def count_rows(self, table_name: str) -> int:
        return len(self.rows.get(table_name, []))

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

    def ensure_catalog(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(CATALOG_DDL)
        self._conn.commit()

    def catalog_get(self, sha256: str, table_name: str) -> CatalogEntry | None:
        sql = f'''
            SELECT source_artifact_sha256, table_name, source_artifact_path,
                   source_artifact_size, row_count, status, loaded_at
            FROM "{CATALOG_TABLE}"
            WHERE source_artifact_sha256 = %s AND table_name = %s
        '''
        with self._conn.cursor() as cur:
            cur.execute(sql, (sha256, table_name))
            row = cur.fetchone()
        if not row:
            return None
        return CatalogEntry(
            source_artifact_sha256=row[0],
            table_name=row[1],
            source_artifact_path=row[2],
            source_artifact_size=row[3],
            row_count=int(row[4]),
            status=row[5],
            loaded_at=row[6],
        )

    def catalog_upsert(self, entry: CatalogEntry) -> None:
        sql = f'''
            INSERT INTO "{CATALOG_TABLE}" (
                source_artifact_sha256, table_name, source_artifact_path,
                source_artifact_size, row_count, status, loaded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_artifact_sha256, table_name) DO UPDATE SET
                source_artifact_path = EXCLUDED.source_artifact_path,
                source_artifact_size = EXCLUDED.source_artifact_size,
                row_count = EXCLUDED.row_count,
                status = EXCLUDED.status,
                loaded_at = EXCLUDED.loaded_at
        '''
        with self._conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    entry.source_artifact_sha256,
                    entry.table_name,
                    entry.source_artifact_path,
                    entry.source_artifact_size,
                    entry.row_count,
                    entry.status,
                    entry.loaded_at or datetime.now(timezone.utc),
                ),
            )
        self._conn.commit()

    def delete_rows_for_artifact(self, table_name: str, sha256: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                f'DELETE FROM "{table_name}" WHERE "source_artifact_sha256" = %s',
                (sha256,),
            )
            n = cur.rowcount
        self._conn.commit()
        return int(n or 0)

    def count_rows(self, table_name: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row = cur.fetchone()
            return int(row[0]) if row else 0

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
        return self.count_rows(table_name)

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
    source_artifact_size: int | None = None,
    on_duplicate: OnDuplicate = "skip",
) -> LoadResult:
    """Ensure table/catalog and insert rows with lineage + idempotency.

    ``on_duplicate=skip``: if catalog already has this sha256+table, skip insert.
    ``on_duplicate=replace``: delete existing rows for this sha256, then re-insert.
    """
    if not schema.columns:
        raise LoadError("schema has no columns")

    sink.ensure_catalog()
    sink.ensure_table(schema)

    existing = sink.catalog_get(source_artifact_sha256, schema.table_name)
    skipped = False
    replaced = False
    inserted = 0

    if existing is not None and existing.status == "loaded":
        if on_duplicate == "skip":
            skipped = True
            entry = existing
            return LoadResult(
                table_name=schema.table_name,
                inserted_rows=0,
                ddl=schema.ddl(include_lineage=True),
                skipped=True,
                replaced=False,
                catalog_entry=entry.to_dict(),
                lineage={
                    "source_artifact_path": source_artifact_path,
                    "source_artifact_sha256": source_artifact_sha256,
                    "inserted_rows": 0,
                    "table_name": schema.table_name,
                    "skipped": True,
                },
            )
        if on_duplicate == "replace":
            sink.delete_rows_for_artifact(schema.table_name, source_artifact_sha256)
            replaced = True

    typed = prepare_typed_rows(schema, rows)
    inserted = sink.insert_rows(
        schema,
        typed,
        source_artifact_path=source_artifact_path,
        source_artifact_sha256=source_artifact_sha256,
        start_row_number=1,
    )
    entry = make_catalog_entry(
        sha256=source_artifact_sha256,
        table_name=schema.table_name,
        path=source_artifact_path,
        size=source_artifact_size,
        row_count=inserted,
        status="loaded",
    )
    sink.catalog_upsert(entry)

    return LoadResult(
        table_name=schema.table_name,
        inserted_rows=inserted,
        ddl=schema.ddl(include_lineage=True),
        skipped=skipped,
        replaced=replaced,
        catalog_entry=entry.to_dict(),
        lineage={
            "source_artifact_path": source_artifact_path,
            "source_artifact_sha256": source_artifact_sha256,
            "inserted_rows": inserted,
            "table_name": schema.table_name,
            "skipped": skipped,
            "replaced": replaced,
        },
    )
