"""PostgreSQL loader with lineage, ingest catalog, and idempotent loads."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol, Sequence

from mhtml_etl_gateway.ingest_catalog import (
    CATALOG_DDL,
    CATALOG_TABLE,
    CatalogEntry,
    make_catalog_entry,
)
from mhtml_etl_gateway.lineage import artifact_reference
from mhtml_etl_gateway.sql_ident import require_safe_ident
from mhtml_etl_gateway.schema_inference import (
    PG_BIGINT,
    PG_BOOLEAN,
    PG_DATE,
    PG_NUMERIC,
    PG_TEXT,
    PG_TIME,
    PG_TIMESTAMP,
    TableSchema,
    coerce_value,
    values_require_text,
)

OnDuplicate = Literal["skip", "replace"]


class LoadError(ValueError):
    """Fail-closed load error."""


@dataclass
class LoadResult:
    """Outcome and SQL evidence produced by one table load."""

    table_name: str
    inserted_rows: int
    ddl: str
    skipped: bool = False
    replaced: bool = False
    catalog_entry: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)


class RowSink(Protocol):
    """Transactional storage contract shared by PostgreSQL and test sinks."""

    def ensure_table(self, schema: TableSchema) -> None:
        """Ensure the target table exists and matches the supplied schema."""
        raise NotImplementedError  # pragma: no cover

    def ensure_catalog(self) -> None:
        """Ensure the idempotency catalog relation exists."""
        raise NotImplementedError  # pragma: no cover

    def catalog_get(self, sha256: str, table_name: str) -> CatalogEntry | None:
        """Return a prior load record for an artifact and table, if present."""
        raise NotImplementedError  # pragma: no cover

    def count_rows(self, table_name: str) -> int:
        """Return the current row count for a validated table name."""
        raise NotImplementedError  # pragma: no cover

    def write_artifact_rows(
        self,
        schema: TableSchema,
        rows: Sequence[Sequence[Any]],
        *,
        source_artifact_path: str,
        source_artifact_sha256: str,
        catalog_entry: CatalogEntry,
        replace_existing: bool,
        start_row_number: int = 1,
    ) -> int:
        """Atomically delete-if-replace + insert + catalog upsert.

        On failure, no partial business-row delete may remain committed while
        catalog still says ``loaded``.
        """
        raise NotImplementedError  # pragma: no cover


def _build_row_records(
    schema: TableSchema,
    rows: Sequence[Sequence[Any]],
    *,
    source_artifact_path: str,
    source_artifact_sha256: str,
    start_row_number: int,
    loaded_at: datetime,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for offset, row in enumerate(rows):
        record: dict[str, Any] = {}
        for i, col in enumerate(schema.columns):
            record[col.db_name] = row[i] if i < len(row) else None
        record["source_artifact_path"] = source_artifact_path
        record["source_artifact_sha256"] = source_artifact_sha256
        record["source_row_number"] = start_row_number + offset
        record["loaded_at"] = loaded_at
        records.append(record)
    return records


class InMemorySink:
    """Injectable sink for unit tests (no live database)."""

    def __init__(self) -> None:
        self.schemas: dict[str, TableSchema] = {}
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self.ddl_statements: list[str] = []
        self.catalog: dict[tuple[str, str], CatalogEntry] = {}
        # Test hook: when True, fail after delete inside write_artifact_rows.
        self.fail_after_delete: bool = False

    def ensure_table(self, schema: TableSchema) -> None:
        """Register a schema and record its DDL in the in-memory sink."""
        self.schemas[schema.table_name] = schema
        self.ddl_statements.append(schema.ddl(include_lineage=True))
        self.rows.setdefault(schema.table_name, [])

    def ensure_catalog(self) -> None:
        """Record creation of the ingest catalog without opening a database."""
        self.ddl_statements.append(CATALOG_DDL)

    def catalog_get(self, sha256: str, table_name: str) -> CatalogEntry | None:
        """Return a previously stored catalog entry, if one exists."""
        return self.catalog.get((sha256, table_name))

    def count_rows(self, table_name: str) -> int:
        """Return the number of rows currently stored for ``table_name``."""
        return len(self.rows.get(table_name, []))

    def write_artifact_rows(
        self,
        schema: TableSchema,
        rows: Sequence[Sequence[Any]],
        *,
        source_artifact_path: str,
        source_artifact_sha256: str,
        catalog_entry: CatalogEntry,
        replace_existing: bool,
        start_row_number: int = 1,
    ) -> int:
        """Atomically replace or append rows and update the in-memory catalog."""
        if schema.table_name not in self.schemas:
            raise LoadError(f"table not ensured: {schema.table_name}")
        # Snapshot for atomic rollback.
        snap_rows = deepcopy(self.rows.get(schema.table_name, []))
        snap_cat = self.catalog.get((source_artifact_sha256, schema.table_name))
        try:
            store = self.rows.setdefault(schema.table_name, [])
            if replace_existing:
                self.rows[schema.table_name] = [
                    r
                    for r in store
                    if r.get("source_artifact_sha256") != source_artifact_sha256
                ]
                store = self.rows[schema.table_name]
            if self.fail_after_delete:
                raise LoadError("simulated insert failure after delete")
            loaded_at = datetime.now(timezone.utc)
            store.extend(
                _build_row_records(
                    schema,
                    rows,
                    source_artifact_path=source_artifact_path,
                    source_artifact_sha256=source_artifact_sha256,
                    start_row_number=start_row_number,
                    loaded_at=loaded_at,
                )
            )
            self.catalog[(catalog_entry.source_artifact_sha256, catalog_entry.table_name)] = (
                catalog_entry
            )
            return len(rows)
        except Exception:
            self.rows[schema.table_name] = snap_rows
            key = (source_artifact_sha256, schema.table_name)
            if snap_cat is None:
                self.catalog.pop(key, None)
            else:
                self.catalog[key] = snap_cat
            raise


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
        """Close the live PostgreSQL connection."""
        self._conn.close()

    def rollback(self) -> None:
        """Clear aborted transaction so batch continue_on_error can proceed."""
        self._conn.rollback()

    def __enter__(self) -> "PsycopgSink":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _execute(self, query, params: Sequence[Any] | None = None) -> None:
        """Run SQL after identifier allow-listing (see require_safe_ident / Identifier).

        Dynamic relation names are unavoidable for multi-table ETL; values always
        use bind parameters. Semgrep cannot prove Identifier safety statically.
        """
        with self._conn.cursor() as cur:
            if params is None:
                # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                cur.execute(query)
            else:
                # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                cur.execute(query, params)

    def _executemany(self, query, params_seq: Sequence[Sequence[Any]]) -> None:
        with self._conn.cursor() as cur:
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cur.executemany(query, params_seq)

    def _fetchone(self, query, params: Sequence[Any] | None = None):
        with self._conn.cursor() as cur:
            if params is None:
                # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                cur.execute(query)
            else:
                # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                cur.execute(query, params)
            return cur.fetchone()

    def _fetchall(self, query, params: Sequence[Any] | None = None) -> list:
        with self._conn.cursor() as cur:
            if params is None:
                # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                cur.execute(query)
            else:
                # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                cur.execute(query, params)
            return list(cur.fetchall())

    def _ensure_missing_columns(self, schema: TableSchema) -> None:
        """Add schema columns missing from an already-existing relation."""
        from psycopg import sql as pgsql

        existing_names = {
            str(name)
            for name, _data_type in self._fetchall(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = %s",
                (schema.table_name,),
            )
        }
        allowed_types = {
            PG_TEXT,
            PG_BOOLEAN,
            PG_BIGINT,
            PG_NUMERIC,
            PG_DATE,
            PG_TIME,
            PG_TIMESTAMP,
        }
        table = require_safe_ident(schema.table_name)
        for column in schema.columns:
            if column.db_name in existing_names:
                continue
            if column.pg_type not in allowed_types:
                raise LoadError("unsupported schema column type")
            self._execute(
                pgsql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} {}").format(
                    pgsql.Identifier(table),
                    pgsql.Identifier(require_safe_ident(column.db_name)),
                    pgsql.SQL(column.pg_type),
                )
            )
            existing_names.add(column.db_name)

    def ensure_table(self, schema: TableSchema) -> None:
        """Create or evolve a table and apply its safe column comments."""
        # DDL identifiers validated inside TableSchema.ddl().  Keep CREATE and
        # COMMENT statements separate so psycopg never has to prepare a
        # multi-command statement, while committing them together.
        self._execute(schema.create_ddl(include_lineage=True))
        self._ensure_missing_columns(schema)
        for statement in schema.comment_ddl():
            self._execute(statement)
        self._conn.commit()

    def ensure_catalog(self) -> None:
        """Create the fixed artifact ingest catalog relation."""
        self._execute(CATALOG_DDL)
        self._conn.commit()

    def catalog_get(self, sha256: str, table_name: str) -> CatalogEntry | None:
        """Fetch one idempotency record using bound values."""
        # Fixed catalog relation; bind parameters for values only.
        query = (
            "SELECT source_artifact_sha256, table_name, source_artifact_path, "
            "source_artifact_size, row_count, status, loaded_at "
            "FROM mhtml_ingest_artifact "
            "WHERE source_artifact_sha256 = %s AND table_name = %s"
        )
        row = self._fetchone(query, (sha256, table_name))
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

    def count_rows(self, table_name: str) -> int:
        """Count rows in a validated PostgreSQL relation."""
        from psycopg import sql as pgsql

        ident = require_safe_ident(table_name)
        query = pgsql.SQL("SELECT COUNT(*) FROM {}").format(pgsql.Identifier(ident))
        row = self._fetchone(query)
        return int(row[0]) if row else 0

    def _columns_to_promote(
        self, schema: TableSchema, rows: Sequence[Sequence[Any]]
    ) -> list[str]:
        """Return db column names that must widen to TEXT for these values.

        A later artifact may infer TEXT because it contains a value outside the
        first artifact's type sample, while the already-created table still has
        BIGINT/DATE/etc. Inspect the live relation as well as the current
        inferred schema so that schema evolution cannot fail at INSERT time.
        Missing columns are added by ``ensure_table`` before this method runs.
        """
        existing_types = {
            str(name): str(data_type).lower()
            for name, data_type in self._fetchall(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = %s",
                (schema.table_name,),
            )
        }
        to_promote: list[str] = []
        for i, col in enumerate(schema.columns):
            prepared = []
            for row in rows:
                raw = row[i] if i < len(row) else None
                prepared.append(
                    coerce_value(str(raw), col.pg_type) if raw is not None else None
                )
            existing_type = existing_types.get(col.db_name)
            if existing_type in {"text", "character varying"}:
                continue
            if existing_type:
                compatible_types = {
                    PG_TEXT: {"text", "character varying"},
                    PG_BIGINT: {"bigint"},
                    PG_NUMERIC: {"numeric", "decimal"},
                    PG_BOOLEAN: {"boolean"},
                    PG_DATE: {"date"},
                    PG_TIME: {"time without time zone"},
                    PG_TIMESTAMP: {"timestamp without time zone"},
                }.get(col.pg_type, {col.pg_type.lower()})
                if (
                    existing_type not in compatible_types
                    or values_require_text(col.pg_type, prepared)
                ):
                    to_promote.append(col.db_name)
                continue
        return to_promote

    def write_artifact_rows(
        self,
        schema: TableSchema,
        rows: Sequence[Sequence[Any]],
        *,
        source_artifact_path: str,
        source_artifact_sha256: str,
        catalog_entry: CatalogEntry,
        replace_existing: bool,
        start_row_number: int = 1,
    ) -> int:
        """Single transaction: promote-if-needed + delete-if-replace + insert + catalog."""
        from psycopg import sql as pgsql

        table = require_safe_ident(schema.table_name)
        to_promote = self._columns_to_promote(schema, rows)
        col_names = [require_safe_ident(c.db_name) for c in schema.columns] + [
            "source_artifact_path",
            "source_artifact_sha256",
            "source_row_number",
        ]
        col_idents = [pgsql.Identifier(n) for n in col_names]
        placeholders = pgsql.SQL(", ").join(pgsql.Placeholder() * len(col_names))
        insert_sql = pgsql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            pgsql.Identifier(table),
            pgsql.SQL(", ").join(col_idents),
            placeholders,
        )
        catalog_sql = (
            "INSERT INTO mhtml_ingest_artifact ("
            "source_artifact_sha256, table_name, source_artifact_path, "
            "source_artifact_size, row_count, status, loaded_at"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (source_artifact_sha256, table_name) DO UPDATE SET "
            "source_artifact_path = EXCLUDED.source_artifact_path, "
            "source_artifact_size = EXCLUDED.source_artifact_size, "
            "row_count = EXCLUDED.row_count, "
            "status = EXCLUDED.status, "
            "loaded_at = EXCLUDED.loaded_at"
        )
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

        try:
            # DDL + DML share one transaction so promote rolls back with insert failure.
            for name in to_promote:
                col = require_safe_ident(name)
                query = pgsql.SQL(
                    "ALTER TABLE {} ALTER COLUMN {} TYPE TEXT USING {}::text"
                ).format(
                    pgsql.Identifier(table),
                    pgsql.Identifier(col),
                    pgsql.Identifier(col),
                )
                self._execute(query)
            if replace_existing:
                del_q = pgsql.SQL(
                    "DELETE FROM {} WHERE source_artifact_sha256 = %s"
                ).format(pgsql.Identifier(table))
                self._execute(del_q, (source_artifact_sha256,))
            if payloads:
                self._executemany(insert_sql, payloads)
            self._execute(
                catalog_sql,
                (
                    catalog_entry.source_artifact_sha256,
                    catalog_entry.table_name,
                    catalog_entry.source_artifact_path,
                    catalog_entry.source_artifact_size,
                    catalog_entry.row_count,
                    catalog_entry.status,
                    catalog_entry.loaded_at or datetime.now(timezone.utc),
                ),
            )
            self._conn.commit()
            return len(payloads)
        except Exception:
            self._conn.rollback()
            raise

    def query_count(self, table_name: str) -> int:
        """Return a queryable row count through the same identifier contract."""
        return self.count_rows(table_name)

    def query_sample(self, table_name: str, limit: int = 5) -> list[tuple]:
        """Return a bounded sample from a validated PostgreSQL relation."""
        from psycopg import sql as pgsql

        ident = require_safe_ident(table_name)
        query = pgsql.SQL("SELECT * FROM {} LIMIT %s").format(pgsql.Identifier(ident))
        return self._fetchall(query, (limit,))


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
    ``on_duplicate=replace``: delete existing rows for this sha256, then re-insert
    **in a single atomic write** (no committed empty state if insert fails).
    """
    if not schema.columns:
        raise LoadError("schema has no columns")
    try:
        expected_artifact_path = artifact_reference(source_artifact_sha256)
    except ValueError:
        raise LoadError("invalid source artifact digest") from None
    if source_artifact_path != expected_artifact_path:
        raise LoadError("source artifact reference does not match source digest")

    sink.ensure_catalog()
    sink.ensure_table(schema)

    existing = sink.catalog_get(source_artifact_sha256, schema.table_name)
    skipped = False
    replaced = False

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
            replaced = True

    typed = prepare_typed_rows(schema, rows)
    entry = make_catalog_entry(
        sha256=source_artifact_sha256,
        table_name=schema.table_name,
        path=source_artifact_path,
        size=source_artifact_size,
        row_count=len(typed),
        status="loaded",
    )
    inserted = sink.write_artifact_rows(
        schema,
        typed,
        source_artifact_path=source_artifact_path,
        source_artifact_sha256=source_artifact_sha256,
        catalog_entry=entry,
        replace_existing=replaced,
        start_row_number=1,
    )

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
