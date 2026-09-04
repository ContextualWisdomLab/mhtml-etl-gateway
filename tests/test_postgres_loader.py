from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from mhtml_etl_gateway.ingest_catalog import (
    CATALOG_STATUS_MIGRATION_DDL,
    CATALOG_STATUS_ROLLBACK_DDL,
)
from mhtml_etl_gateway.lineage import artifact_reference
from mhtml_etl_gateway.pipeline import (
    convert_mhtml_to_postgres,
    extract_table,
    infer_schema_for_extract,
)
from mhtml_etl_gateway.postgres_loader import (
    InMemorySink,
    LoadError,
    PsycopgSink,
    _legacy_column_names,
    load_table,
)
from mhtml_etl_gateway.schema_inference import (
    PG_BIGINT,
    PG_DATE,
    PG_TEXT,
    ColumnSpec,
    TableSchema,
    to_table_name,
)


def test_inmemory_loader_with_lineage(sample_mhtml_path) -> None:
    extracted = extract_table(sample_mhtml_path)
    schema = infer_schema_for_extract(extracted, table_name="zcrht811_export_rows")
    sink = InMemorySink()
    result = load_table(
        schema,
        extracted.rows,
        sink=sink,
        source_artifact_path=extracted.source_path,
        source_artifact_sha256=extracted.source_sha256,
    )
    assert result.inserted_rows == len(extracted.rows)
    assert result.inserted_rows >= 1
    stored = sink.rows["zcrht811_export_rows"]
    assert len(stored) == result.inserted_rows
    row0 = stored[0]
    assert row0["mandt_field"] == 603
    assert row0["guid_field"] == "0050569512931FE183BEBA5F974B88B9"
    assert row0["source_artifact_sha256"] == extracted.source_sha256
    assert row0["source_artifact_path"] == extracted.source_path
    assert extracted.source_path.startswith("artifact:")
    assert str(sample_mhtml_path) not in extracted.source_path
    assert row0["source_row_number"] == 1
    assert "source_artifact_sha256" in result.ddl


def test_load_fails_without_columns() -> None:
    from mhtml_etl_gateway.schema_inference import TableSchema

    sink = InMemorySink()
    with pytest.raises(LoadError):
        load_table(
            TableSchema(table_name="empty_table", columns=[]),
            [],
            sink=sink,
            source_artifact_path="x",
            source_artifact_sha256="y",
        )


def test_load_rejects_non_opaque_source_reference() -> None:
    schema = TableSchema(
        table_name="mhtml_rows",
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )
    with pytest.raises(LoadError, match="does not match"):
        load_table(
            schema,
            [["sample"]],
            sink=InMemorySink(),
            source_artifact_path="operator-supplied-path",
            source_artifact_sha256="a" * 64,
        )

    assert artifact_reference("a" * 64) == "artifact:aaaaaaaaaaaaaaaa"


def test_pipeline_dry_run_end_to_end(sample_mhtml_path, tmp_path) -> None:
    lineage = tmp_path / "lineage.json"
    result = convert_mhtml_to_postgres(
        sample_mhtml_path,
        table_name="zcrht811_export_rows",
        lineage_json=lineage,
    )
    assert result["inserted_rows"] >= 1
    assert "MANDT" in result["headers"]
    assert "GUID" in result["headers"]
    assert result["queryable"]["db_row_count"] >= 1
    assert lineage.is_file()
    text = lineage.read_text(encoding="utf-8")
    assert result["source_sha256"] in text


def test_live_type_promotion_checks_existing_relation_type() -> None:
    sink = object.__new__(PsycopgSink)
    sink._fetchall = lambda query, params=None: [
        ("mixed_value", "bigint"),
        ("already_text", "text"),
        ("typed_mismatch", "bigint"),
    ]
    schema = TableSchema(
        table_name="mhtml_rows",
        columns=[
            ColumnSpec("MIXED_VALUE", "mixed_value", PG_TEXT),
            ColumnSpec("ALREADY_TEXT", "already_text", PG_BIGINT),
            ColumnSpec("TYPED_MISMATCH", "typed_mismatch", PG_DATE),
        ],
    )

    assert sink._columns_to_promote(schema, [["sample-text", "12", "2024-01-01"]]) == [
        "mixed_value",
        "typed_mismatch",
    ]


def test_live_sink_adds_missing_columns() -> None:
    sink = object.__new__(PsycopgSink)
    statements: list[str] = []
    sink._fetchall = lambda query, params=None: [("existing_value", "text")]
    sink._execute = lambda query, params=None: statements.append(str(query))
    schema = TableSchema(
        table_name="mhtml_rows",
        columns=[
            ColumnSpec("EXISTING_VALUE", "existing_value", PG_TEXT),
            ColumnSpec("ADDED_VALUE", "added_value", PG_BIGINT),
        ],
    )

    sink._ensure_missing_columns(schema)

    assert len(statements) == 1
    assert "ADD COLUMN IF NOT EXISTS" in statements[0]
    assert "added_value" in statements[0]
    assert "BIGINT" in statements[0]


def test_live_sink_rejects_parallel_legacy_column_creation() -> None:
    """An upgrade must not split old and new values across parallel columns."""
    sink = object.__new__(PsycopgSink)
    statements: list[str] = []
    sink._fetchall = lambda query, params=None: [("mandt", "bigint")]
    sink._execute = lambda query, params=None: statements.append(str(query))
    schema = TableSchema(
        table_name="mhtml_rows",
        columns=[ColumnSpec("MANDT", "mandt_field", PG_BIGINT)],
    )

    with pytest.raises(LoadError, match=r"legacy column requires explicit migration"):
        sink._ensure_missing_columns(schema)

    assert statements == []


def test_live_sink_rejects_legacy_column_when_successor_already_exists() -> None:
    """A dual-column state remains blocked until an explicit migration."""
    sink = object.__new__(PsycopgSink)
    sink._fetchall = lambda query, params=None: [
        ("mandt", "bigint"),
        ("mandt_field", "bigint"),
    ]
    schema = TableSchema(
        table_name="mhtml_rows",
        columns=[ColumnSpec("MANDT", "mandt_field", PG_BIGINT)],
    )

    with pytest.raises(LoadError, match=r"legacy column requires explicit migration"):
        sink._ensure_missing_columns(schema)


def test_legacy_column_detection_reconstructs_numeric_and_duplicate_names() -> None:
    """Upgrade detection reproduces the pre-policy collision behavior exactly."""
    schema = TableSchema(
        table_name="mhtml_rows",
        columns=[
            ColumnSpec("1VALUE", "col_1value", PG_TEXT),
            ColumnSpec("A", "a_field", PG_TEXT),
            ColumnSpec("A", "a_field_2", PG_TEXT),
        ],
    )

    assert _legacy_column_names(schema) == ["col_1_value", "a", "a_2"]


def test_live_sink_rejects_parallel_legacy_table_creation() -> None:
    """An upgrade must not create a suffixed table beside persisted rows."""
    sink = object.__new__(PsycopgSink)
    statements: list[str] = []
    sink._fetchall = lambda query, params=None: [("simple",)]
    sink._execute = lambda query, params=None: statements.append(str(query))
    sink._conn = SimpleNamespace(commit=lambda: None)
    schema = TableSchema(
        table_name="simple_table",
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )

    with pytest.raises(LoadError, match=r"legacy table requires explicit migration"):
        sink.ensure_table(schema)

    assert statements == []


@pytest.mark.parametrize("length", [58, 63, 80])
def test_live_sink_rejects_full_boundary_legacy_table_candidate(length: int) -> None:
    """The lookup must include the pre-policy name, not a suffix-stripped cut."""
    source_name = "x" * length
    legacy_name = source_name[:63]
    schema = TableSchema(
        table_name=to_table_name(source_name),
        source_table_name=source_name,
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )
    sink = object.__new__(PsycopgSink)
    observed: list[tuple[str, ...]] = []

    def fetchall(query, params=None):
        # params is (list(query_names),)
        observed.append(tuple(params or ()))
        return [(legacy_name,)]

    sink._fetchall = fetchall

    with pytest.raises(LoadError, match=r"legacy table requires explicit migration"):
        sink._reject_legacy_table_split(schema)

    assert legacy_name in observed[0][0]


def test_live_sink_queries_numeric_legacy_table_candidate() -> None:
    source_name = "1" + "x" * 62
    legacy_name = f"col_{source_name}"[:63]
    schema = TableSchema(
        table_name=to_table_name(source_name),
        source_table_name=source_name,
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )
    sink = object.__new__(PsycopgSink)
    sink._fetchall = lambda query, params=None: [(legacy_name,)]

    with pytest.raises(LoadError, match=r"legacy table requires explicit migration"):
        sink._reject_legacy_table_split(schema)


def test_live_sink_allows_nonlegacy_or_already_migrated_table_names() -> None:
    """The split guard is a narrow upgrade boundary, not a general DDL blocker."""
    sink = object.__new__(PsycopgSink)
    sink._fetchall = lambda query, params=None: (_ for _ in ()).throw(
        AssertionError("no legacy lookup expected")
    )
    sink._reject_legacy_table_split(
        TableSchema(
            table_name="already_multiword_table",
            columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
        )
    )

    sink._fetchall = lambda query, params=None: [("simple",), ("simple_table",)]
    with pytest.raises(LoadError, match=r"legacy table requires explicit migration"):
        sink._reject_legacy_table_split(
            TableSchema(
                table_name="simple_table",
                columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
            )
        )

    sink._fetchall = lambda query, params=None: [("simple_table",)]
    sink._reject_legacy_table_split(
        TableSchema(
            table_name="simple_table",
            columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
        )
    )


def test_catalog_status_migration_has_explicit_fail_closed_up_and_down_paths() -> None:
    """Catalog upgrades and application rollbacks must be symmetric and safe."""
    assert "RENAME COLUMN status TO load_status_code" in CATALOG_STATUS_MIGRATION_DDL
    assert "RENAME COLUMN load_status_code TO status" in CATALOG_STATUS_ROLLBACK_DDL
    for ddl in (CATALOG_STATUS_MIGRATION_DDL, CATALOG_STATUS_ROLLBACK_DDL):
        assert "RAISE EXCEPTION" in ddl
        assert "column_name = 'status'" in ddl
        assert "column_name = 'load_status_code'" in ddl


@pytest.mark.skipif(
    not os.environ.get("MHTML_ETL_DSN") and not os.environ.get("DATABASE_URL"),
    reason="No PostgreSQL DSN set (MHTML_ETL_DSN / DATABASE_URL)",
)
def test_live_postgres_load(sample_mhtml_path) -> None:
    dsn = os.environ.get("MHTML_ETL_DSN") or os.environ.get("DATABASE_URL")
    table = "zcrht811_fixture_test_rows"
    # replace first so re-runs of the suite stay stable
    result = convert_mhtml_to_postgres(
        sample_mhtml_path,
        dsn=dsn,
        table_name=table,
        on_duplicate="replace",
    )
    assert result["inserted_rows"] >= 1
    assert result["queryable"]["db_row_count"] >= 1
    assert result.get("catalog")
