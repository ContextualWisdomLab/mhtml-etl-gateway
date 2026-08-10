from __future__ import annotations

from mhtml_etl_gateway.pipeline import extract_table, infer_schema_for_extract
from mhtml_etl_gateway.schema_inference import (
    PG_BIGINT,
    PG_BOOLEAN,
    PG_DATE,
    PG_NUMERIC,
    PG_TEXT,
    PG_TIME,
    infer_pg_type,
    infer_table_schema,
    to_snake_case,
)


def test_to_snake_case_multiword() -> None:
    assert to_snake_case("VOC_PUCODE") == "voc_pucode"
    assert to_snake_case("MANDT") == "mandt"
    assert to_snake_case("ZCRHT811 Export Rows") == "zcrht811_export_rows"
    assert to_snake_case("123abc") == "col_123abc"


def test_infer_pg_types_unit() -> None:
    assert infer_pg_type(["true", "false"]) == PG_BOOLEAN
    assert infer_pg_type(["1", "2", "99"]) == PG_BIGINT
    assert infer_pg_type(["1.5", "2.0"]) == PG_NUMERIC
    assert infer_pg_type(["2026-02-20", "2026-02-21"]) == PG_DATE
    assert infer_pg_type(["09:48:09", "11:17:26"]) == PG_TIME
    assert infer_pg_type(["hello", "world"]) == PG_TEXT
    assert infer_pg_type(["", ""]) == PG_TEXT


def test_schema_from_fixture_pipeline(sample_mhtml_path) -> None:
    extracted = extract_table(sample_mhtml_path)
    schema = infer_schema_for_extract(extracted, table_name="zcrht811_export_rows")
    assert schema.table_name == "zcrht811_export_rows"
    type_map = schema.type_map()
    assert "MANDT" in type_map
    assert "GUID" in type_map
    assert type_map["MANDT"] == PG_BIGINT
    assert type_map["GUID"] == PG_TEXT
    assert type_map["ERDAT"] == PG_DATE
    assert type_map["ERZET"] == PG_TIME
    assert type_map["AMOUNT"] in {PG_NUMERIC, PG_BIGINT}
    ddl = schema.ddl(include_lineage=True)
    assert "CREATE TABLE IF NOT EXISTS" in ddl
    assert "source_artifact_sha256" in ddl
    assert "source_row_number" in ddl
    # multiword snake_case columns
    assert "mandt" in ddl
    assert "voc_pucode" in ddl


def test_unique_snake_collision() -> None:
    schema = infer_table_schema(["FOO", "foo", "Foo Bar"], [["1", "2", "x"]])
    names = [c.db_name for c in schema.columns]
    assert names[0] == "foo"
    assert names[1] == "foo_2"
    assert names[2] == "foo_bar"
