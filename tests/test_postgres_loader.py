from __future__ import annotations

import os

import pytest

from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres, extract_table, infer_schema_for_extract
from mhtml_etl_gateway.postgres_loader import InMemorySink, LoadError, PsycopgSink, load_table


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
    assert row0["mandt"] == 603
    assert row0["guid"] == "0050569512931FE183BEBA5F974B88B9"
    assert row0["source_artifact_sha256"] == extracted.source_sha256
    assert row0["source_artifact_path"] == extracted.source_path
    assert row0["source_row_number"] == 1
    assert "source_artifact_sha256" in result.ddl


def test_load_fails_without_columns() -> None:
    from mhtml_etl_gateway.schema_inference import TableSchema

    sink = InMemorySink()
    with pytest.raises(LoadError):
        load_table(
            TableSchema(table_name="empty", columns=[]),
            [],
            sink=sink,
            source_artifact_path="x",
            source_artifact_sha256="y",
        )


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
    sample = result["queryable"]["sample"]
    assert sample
    assert result.get("catalog")
