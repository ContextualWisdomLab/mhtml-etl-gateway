from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from mhtml_etl_gateway.pipeline import extract_table, infer_schema_for_extract
from mhtml_etl_gateway.schema_inference import (
    PG_BIGINT,
    PG_BOOLEAN,
    PG_DATE,
    PG_NUMERIC,
    PG_TEXT,
    PG_TIME,
    PG_TIMESTAMP,
    _is_time,
    coerce_value,
    infer_pg_type,
    infer_table_schema,
    to_table_name,
    to_snake_case,
    values_require_text,
)


def test_to_snake_case_multiword() -> None:
    assert to_snake_case("VOC_PUCODE") == "voc_pucode"
    assert to_snake_case("MANDT") == "mandt_field"
    assert to_snake_case("ZCRHT811 Export Rows") == "zcrht811_export_rows"
    assert to_snake_case("123abc") == "col_123abc"
    assert to_table_name("simple") == "simple_table"
    assert to_table_name("simple_rows") == "simple_rows"


def test_infer_pg_types_unit() -> None:
    assert infer_pg_type(["true", "false"]) == PG_BOOLEAN
    assert infer_pg_type(["1", "2", "99"]) == PG_BIGINT
    assert infer_pg_type(["1.5", "2.0"]) == PG_NUMERIC
    assert infer_pg_type(["2026-02-20", "2026-02-21"]) == PG_DATE
    assert infer_pg_type(["09:48:09", "11:17:26"]) == PG_TIME
    assert infer_pg_type(["hello", "world"]) == PG_TEXT
    assert infer_pg_type(["", ""]) == PG_TEXT
    assert _is_time("9:48:09") is True


def test_iso_coercion_and_timezone_preservation() -> None:
    timestamp = coerce_value("2026-02-20T12:00:00", PG_TIMESTAMP)
    assert isinstance(timestamp, datetime)
    assert timestamp == datetime(2026, 2, 20, 12, 0, 0)
    assert infer_pg_type(["2026-02-20T12:00:00"]) == PG_TIMESTAMP
    assert coerce_value("2026-02-20", PG_DATE) == date(2026, 2, 20)
    assert coerce_value("09:48:09", PG_TIME) == time(9, 48, 9)
    assert coerce_value("094809", PG_TIME) == time(9, 48, 9)
    assert coerce_value("20-02-2026", PG_DATE) == "20-02-2026"

    legacy_timestamp = coerce_value("2026/02/20 12:00:00", PG_TIMESTAMP)
    assert legacy_timestamp == datetime(2026, 2, 20, 12, 0, 0)

    offset_timestamp = "2026-02-20T12:00:00+09:00"
    assert infer_pg_type([offset_timestamp]) == PG_TEXT
    assert coerce_value(offset_timestamp, PG_TIMESTAMP) == offset_timestamp

    offset_time = "09:48:09+09:00"
    assert infer_pg_type([offset_time]) == PG_TEXT
    assert coerce_value(offset_time, PG_TIME) == offset_time


@pytest.mark.parametrize(
    ("pg_type", "valid", "invalid"),
    [
        (PG_BIGINT, 1, "1"),
        (PG_NUMERIC, Decimal("1.5"), "1.5"),
        (PG_BOOLEAN, True, "true"),
        (PG_DATE, date(2026, 2, 20), "2026-02-20"),
        (PG_TIME, time(9, 48, 9), "09:48:09"),
        (PG_TIMESTAMP, datetime(2026, 2, 20, 12, 0, 0), "2026-02-20T12:00:00"),
    ],
)
def test_values_require_text_accepts_valid_values_and_rejects_invalid(
    pg_type: str, valid: object, invalid: object
) -> None:
    assert values_require_text(pg_type, (None, valid)) is False
    assert values_require_text(pg_type, (None, invalid)) is True


def test_values_require_text_short_circuits_one_shot_iterables() -> None:
    consumed: list[int] = []

    def prepared_values():
        consumed.append(1)
        yield 1
        consumed.append(2)
        yield "invalid"
        consumed.append(3)
        raise AssertionError("values_require_text did not short-circuit")

    assert values_require_text(PG_BIGINT, prepared_values()) is True
    assert consumed == [1, 2]


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
    assert "mandt_field" in ddl
    assert "voc_pucode" in ddl


def test_unique_snake_collision() -> None:
    schema = infer_table_schema(["FOO", "foo", "Foo Bar"], [["1", "2", "x"]])
    names = [c.db_name for c in schema.columns]
    assert names[0] == "foo_field"
    assert names[1] == "foo_field_2"
    assert names[2] == "foo_bar"
    # Secondary collision: base + suffix already used as a header.
    schema2 = infer_table_schema(["A", "A_2", "A"], [["1", "2", "3"]])
    names2 = [c.db_name for c in schema2.columns]
    assert len(names2) == len(set(names2))
    assert names2[0] == "a_field"
    assert "a_2" in names2
