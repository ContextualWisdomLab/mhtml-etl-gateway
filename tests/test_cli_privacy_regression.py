"""Regression tests for value-free public CLI load summaries."""

from __future__ import annotations

import argparse
import json

import pytest

from mhtml_etl_gateway import cli


def _load_args(source_path: str, *, as_json: bool) -> argparse.Namespace:
    """Build the bounded argument contract consumed by the load command."""

    return argparse.Namespace(
        mhtml_path=source_path,
        required_headers=None,
        on_duplicate="skip",
        dry_run=True,
        dsn=None,
        table_name=None,
        column_mapping=None,
        lineage_json=None,
        ddl_out=None,
        as_json=as_json,
    )


@pytest.mark.parametrize("as_json", [False, True])
def test_run_load_public_output_never_reflects_source_values(
    tmp_path, monkeypatch, capsys, as_json: bool
) -> None:
    """Both public load renderings expose opaque metadata, never source values."""

    source = tmp_path / "private-customer-file.mhtml"
    source.write_bytes(b"fixture")
    private_path = "/tenant/acme/private-customer-file.mhtml"
    decoded_header = "<script>customer_secret()</script>"
    digest = "a" * 64

    monkeypatch.setattr(
        cli,
        "convert_mhtml_to_postgres",
        lambda *args, **kwargs: {
            "headers": [decoded_header, "<b>account_name</b>"],
            "data_row_count": 1,
            "inserted_rows": 1,
            "skipped": False,
            "table_name": "customer_records",
            "lineage": {"source_artifact_path": private_path},
            "queryable": {"db_row_count": 1},
            "source_sha256": digest,
            "ddl": "CREATE TABLE customer_records (...);",
        },
    )

    assert cli._run_load(_load_args(str(source), as_json=as_json)) == 0
    rendered = capsys.readouterr().out

    assert "header_count" in rendered
    assert "artifact:aaaaaaaaaaaaaaaa" in rendered
    assert private_path not in rendered
    assert decoded_header not in rendered
    assert "<script>" not in rendered
    assert '"headers"' not in rendered
    assert "headers:" not in rendered


def test_safe_load_summary_never_reflects_decoded_header_values() -> None:
    """The summary helper exposes a count, never decoded source header text."""

    summary = cli._safe_load_summary(
        {
            "headers": [
                "<script>header()</script>",
                "<script>xheader()</script>",
            ],
            "source_sha256": "b" * 64,
            "lineage": {"source_artifact_path": "/private/local/source.mhtml"},
        }
    )

    assert summary["header_count"] == 2
    assert summary["artifact_ref"] == "artifact:bbbbbbbbbbbbbbbb"
    assert "headers" not in summary
    serialized = json.dumps(summary)
    assert "script" not in serialized
    assert "header()" not in serialized
    assert "/private/local/source.mhtml" not in serialized
