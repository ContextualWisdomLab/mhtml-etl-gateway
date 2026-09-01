"""Naming contract for the persisted ingest catalog boundary."""

from dataclasses import fields

from mhtml_etl_gateway.ingest_catalog import CatalogEntry, make_catalog_entry


def test_catalog_entry_uses_persisted_load_status_language() -> None:
    """Keep internal catalog language aligned with the persisted status column."""
    field_names = {field.name for field in fields(CatalogEntry)}

    assert "load_status_code" in field_names
    assert "status" not in field_names


def test_catalog_entry_preserves_legacy_serialized_status_key() -> None:
    """Keep existing pipeline payloads stable at the serialization boundary."""
    catalog_entry = make_catalog_entry(
        source_artifact_sha256="a" * 64,
        table_name="customer_case_records",
        source_artifact_path="sha256:" + "a" * 64,
        source_artifact_size=12,
        row_count=3,
        load_status_code="loaded",
    )

    assert catalog_entry.load_status_code == "loaded"
    catalog_payload = catalog_entry.to_dict()
    assert catalog_payload["status"] == "loaded"
    assert "load_status_code" not in catalog_payload
