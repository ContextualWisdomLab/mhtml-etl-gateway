"""Schema contracts for business columns colliding with system lineage names."""

from __future__ import annotations

from mhtml_etl_gateway.schema_inference import infer_table_schema


LINEAGE_NAMES = (
    "source_artifact_path",
    "source_artifact_sha256",
    "source_row_number",
    "loaded_at",
)


def test_inferred_business_columns_cannot_claim_system_lineage_names() -> None:
    """Real header normalization must reserve every system-lineage identifier."""
    headers = [
        "SOURCE ARTIFACT PATH",
        "source-artifact-path",
        "SOURCE ARTIFACT SHA256",
        "SOURCE ROW NUMBER",
        "LOADED AT",
    ]
    schema = infer_table_schema(headers, [["a", "b", "c", "1", "2026-09-12"]])

    business_names = [column.db_name for column in schema.columns]
    assert business_names == [
        "source_artifact_path_2",
        "source_artifact_path_3",
        "source_artifact_sha256_2",
        "source_row_number_2",
        "loaded_at_2",
    ]
    assert not set(business_names).intersection(LINEAGE_NAMES)

    ddl = schema.create_ddl(include_lineage=True)
    for lineage_name in LINEAGE_NAMES:
        assert ddl.count(f"    {lineage_name} ") == 1


def test_reserved_name_suffixing_remains_bounded_and_deterministic() -> None:
    """Reservation composes with ordinary business-name collision handling."""
    schema = infer_table_schema(
        ["LOADED AT", "loaded_at", "loaded at 2", "loaded_at_2"],
        [["a", "b", "c", "d"]],
    )

    names = [column.db_name for column in schema.columns]
    assert names == ["loaded_at_2", "loaded_at_3", "loaded_at_2_2", "loaded_at_2_3"]
    assert len(names) == len(set(names))
    assert all(len(name) <= 63 for name in names)
