from __future__ import annotations

import os

import pytest

from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres
from mhtml_etl_gateway.postgres_loader import InMemorySink


def test_idempotent_skip_stable_row_count(sample_mhtml_path) -> None:
    sink = InMemorySink()
    r1 = convert_mhtml_to_postgres(
        sample_mhtml_path,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="skip",
    )
    assert r1["inserted_rows"] >= 1
    assert r1["skipped"] is False
    count1 = sink.count_rows("zcrht811_export_rows")
    assert count1 == r1["inserted_rows"]

    r2 = convert_mhtml_to_postgres(
        sample_mhtml_path,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="skip",
    )
    assert r2["skipped"] is True
    assert r2["inserted_rows"] == 0
    count2 = sink.count_rows("zcrht811_export_rows")
    assert count2 == count1  # no growth (fixes 14→28 class bug)
    assert sink.catalog_get(r1["source_sha256"], "zcrht811_export_rows") is not None


def test_idempotent_replace_rewrites_same_count(sample_mhtml_path) -> None:
    sink = InMemorySink()
    r1 = convert_mhtml_to_postgres(
        sample_mhtml_path,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="replace",
    )
    c1 = sink.count_rows("zcrht811_export_rows")
    r2 = convert_mhtml_to_postgres(
        sample_mhtml_path,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="replace",
    )
    assert r2["replaced"] is True
    c2 = sink.count_rows("zcrht811_export_rows")
    assert c2 == c1
    assert r2["inserted_rows"] == r1["inserted_rows"]


@pytest.mark.skipif(
    not os.environ.get("MHTML_ETL_DSN") and not os.environ.get("DATABASE_URL"),
    reason="No PostgreSQL DSN",
)
def test_live_pg_idempotent_skip(sample_mhtml_path) -> None:
    dsn = os.environ.get("MHTML_ETL_DSN") or os.environ.get("DATABASE_URL")
    table = "zcrht811_idempotent_live"
    # Clean slate via replace first
    convert_mhtml_to_postgres(
        sample_mhtml_path, dsn=dsn, table_name=table, on_duplicate="replace"
    )
    r1 = convert_mhtml_to_postgres(
        sample_mhtml_path, dsn=dsn, table_name=table, on_duplicate="skip"
    )
    # First after replace may insert; second skip
    r2 = convert_mhtml_to_postgres(
        sample_mhtml_path, dsn=dsn, table_name=table, on_duplicate="skip"
    )
    assert r2["skipped"] is True
    assert r2["queryable"]["db_row_count"] == r1["queryable"]["db_row_count"]
    assert r2["queryable"]["db_row_count"] >= 1
