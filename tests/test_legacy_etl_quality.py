"""Realistic and fail-closed coverage for the reusable ETL support layers."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, time, timezone
from io import StringIO
import argparse
import json
from pathlib import Path
import zipfile
from unittest.mock import patch

import pytest

import mhtml_etl_gateway.batch as batch_module
import mhtml_etl_gateway.column_mapping as mapping_module
import mhtml_etl_gateway.cli as cli_module
import mhtml_etl_gateway.html_table_extractor as html_module
import mhtml_etl_gateway.mhtml_parser as mhtml_module
import mhtml_etl_gateway.pipeline as pipeline_module
from mhtml_etl_gateway.lineage import (
    artifact_reference,
    build_lineage,
    sha256_bytes,
    sha256_file,
    write_lineage_json,
)
from mhtml_etl_gateway.ingest_catalog import make_catalog_entry
from mhtml_etl_gateway.postgres_loader import (
    InMemorySink,
    LoadError,
    PsycopgSink,
    load_table,
    prepare_typed_rows,
)
from mhtml_etl_gateway.schema_inference import (
    PG_BIGINT,
    PG_BOOLEAN,
    PG_DATE,
    PG_NUMERIC,
    PG_TEXT,
    PG_TIME,
    PG_TIMESTAMP,
    ColumnSpec,
    SchemaInferenceError,
    TableSchema,
    _parse_decimal,
    _parse_int,
    coerce_value,
    infer_pg_type,
    infer_table_schema,
    to_snake_case,
    unique_snake_names,
    values_require_text,
)
from mhtml_etl_gateway.sql_ident import UnsafeIdentifierError, quote_sql_literal, require_safe_ident
from mhtml_etl_gateway.validation_engine import (
    DEFAULT_REQUIRED_HEADERS,
    ValidationError,
    is_zcrht811_shaped,
    resolve_required_headers,
    validate_extracted_table,
)
from tests.fixture_factory import make_mhtml


def test_lineage_file_and_error_contracts(tmp_path: Path) -> None:
    """File-backed and byte-backed lineage preserve opaque identity only."""
    source = tmp_path / "customer-export.mhtml"
    source.write_bytes(b"alpha\nbeta")
    digest = sha256_file(source, chunk_size=2)
    assert digest == sha256_bytes(source.read_bytes())
    loaded_at = datetime(2026, 8, 11, tzinfo=timezone.utc)
    lineage = build_lineage(
        source,
        row_count=2,
        table_name="customer_export_rows",
        loaded_at=loaded_at,
    )
    assert lineage.source_artifact_path == artifact_reference(digest)
    assert lineage.source_artifact_size == source.stat().st_size
    assert lineage.source_artifact_mtime_ns is not None
    target = write_lineage_json(lineage, tmp_path / "nested" / "lineage.json")
    assert json.loads(target.read_text(encoding="utf-8"))["row_count"] == 2

    byte_lineage = build_lineage(
        tmp_path / "not-created.mhtml",
        data=b"bytes",
        row_count=1,
        table_name="byte_rows",
        source_artifact_path=artifact_reference(sha256_bytes(b"bytes")),
        loaded_at=loaded_at,
    )
    assert byte_lineage.source_artifact_size == 5
    with pytest.raises(ValueError, match="without source"):
        build_lineage(tmp_path / "missing.mhtml", row_count=0, table_name="empty_rows")
    with pytest.raises(ValueError, match="does not match"):
        build_lineage(
            source,
            row_count=1,
            table_name="customer_export_rows",
            source_artifact_path="artifact:0000000000000000",
        )
    with pytest.raises(ValueError):
        artifact_reference("not-a-digest")
    with pytest.raises(ValueError):
        artifact_reference("g" * 64)


def test_mhtml_parser_supports_bare_html_and_defensive_payloads(tmp_path: Path) -> None:
    """Bare worksheets and non-standard MIME payloads follow bounded paths."""
    html = b"<html><body><table><tr><td>A</td></tr></table></body></html>"
    assert mhtml_module._looks_like_mhtml(b"Content-Type: text/html\n")
    assert mhtml_module._looks_like_mhtml(b"multipart/related\n")
    assert mhtml_module._looks_like_mhtml(html)
    assert not mhtml_module._looks_like_mhtml(b"plain text")
    parts = mhtml_module.parse_mhtml_parts(html)
    assert parts[0].content_type == "text/plain"
    assert mhtml_module.extract_html_bytes(html) == html

    source = tmp_path / "bare.mhtml"
    source.write_bytes(html)
    assert mhtml_module.read_mhtml_file(source, chunk_size=3) == html
    raw, selected = mhtml_module.extract_html_from_path(source)
    assert raw == selected == html
    with pytest.raises(FileNotFoundError):
        mhtml_module.read_mhtml_file(tmp_path / "missing.mhtml")

    class FakePart:
        def __init__(self, decoded, raw, charset="utf-8") -> None:
            self.decoded = decoded
            self.raw = raw
            self.charset = charset

        def get_payload(self, *, decode):
            return self.decoded if decode else self.raw

        def get_content_charset(self):
            return self.charset

    assert mhtml_module._decode_part_payload(FakePart(b"decoded", "ignored")) == b"decoded"
    assert mhtml_module._decode_part_payload(FakePart(None, b"raw")) == b"raw"
    assert mhtml_module._decode_part_payload(FakePart(None, "한글", "utf-8")) == "한글".encode()
    assert mhtml_module._decode_part_payload(FakePart(None, "text", "not-a-charset")) == b"text"
    assert mhtml_module._decode_part_payload(FakePart(None, "")) is None

    with pytest.raises(mhtml_module.MhtmlParseError, match="no MIME parts"):
        mhtml_module.parse_mhtml_parts(b"MIME-Version: 1.0\n")
    with patch.object(mhtml_module, "_decode_part_payload", return_value=None):
        fallback_parts = mhtml_module.parse_mhtml_parts(html)
    assert fallback_parts[0].payload == html
    no_html_parts = [mhtml_module.MimePart("text/plain", None, b"<table>ordinary text")]
    with patch("mhtml_etl_gateway.mhtml_parser.parse_mhtml_parts", return_value=no_html_parts):
        assert mhtml_module.extract_html_bytes(b"ignored") == b"<table>ordinary text"
    with patch(
        "mhtml_etl_gateway.mhtml_parser.parse_mhtml_parts",
        return_value=[mhtml_module.MimePart("application/octet-stream", None, b"binary")],
    ), pytest.raises(mhtml_module.MhtmlParseError, match="no HTML part"):
        mhtml_module.extract_html_bytes(b"ignored")


def test_html_table_extractor_handles_legacy_cells_and_fail_closed_inputs() -> None:
    """Nested worksheet markup, empty cells, spans, and malformed spans are explicit."""
    html = """
    <div>outside</div>
    <table><tr><th colspan="2">Header</th><th x:str="Fallback"></th><th></th></tr>
      <tr><td>A<br>B<table><tr><td>nested<br>value</td></tr></table></td><td> </td><td>C</td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
    </table>
    <table><tr><br></tr></table>
    <table><tr><th></th></tr></table>
    <table></table>
    """
    tables = html_module.extract_tables_from_html(html)
    assert tables[0].headers == ["Header", "Header", "Fallback", "col_4"]
    assert tables[0].rows == [["A\nBnested\nvalue", "", "C"]]
    assert html_module.rows_as_dicts(tables[0])[0]["col_4"] == ""
    assert tables[0].column_count == 4
    assert tables[0].row_count == 1
    html_module.assert_headers_present(tables[0], ["Header"])
    with pytest.raises(html_module.TableExtractError, match="missing required"):
        html_module.assert_headers_present(tables[0], ["missing"])
    with pytest.raises(html_module.TableExtractError, match="empty HTML"):
        html_module.extract_tables_from_html(b" ")
    with pytest.raises(html_module.TableExtractError, match="no HTML tables"):
        html_module.extract_primary_table("<p>no table</p>")

    with pytest.raises(html_module.TableExtractError, match="invalid colspan"):
        html_module.extract_tables_from_html("<table><tr><th colspan='bad'>x</th></tr></table>")
    with pytest.raises(html_module.TableExtractError, match="colspan too large"):
        html_module.extract_tables_from_html("<table><tr><th colspan='100001'>x</th></tr></table>")

    parser = html_module._TopLevelTableParser()
    parser._table_depth = 1
    parser._in_td = True
    parser._cur_row = None
    with pytest.raises(html_module.TableExtractError, match="open row"):
        parser.handle_endtag("td")
    parser.handle_data("ignored after reset")
    parser = html_module._TopLevelTableParser()
    parser._table_depth = 1
    parser.handle_endtag("tr")
    parser._in_tr = True
    parser._cur_row = None
    parser._cur_table = []
    parser.handle_endtag("tr")

    large = "<table><tr><th>A</th></tr><tr><td>" + ("x" * 300_000) + "</td></tr></table>"
    assert html_module.extract_tables_from_html(large)[0].row_count == 1
    with patch.object(
        html_module, "extract_tables_from_html", return_value=[html_module.ExtractedTable([], [])]
    ), pytest.raises(
        html_module.TableExtractError, match="primary table"
    ):
        html_module.extract_primary_table("ignored")


def test_batch_discovery_and_sanitized_failure_paths(tmp_path: Path) -> None:
    """Directory, absolute-glob, relative-glob, limit, and rollback paths are covered."""
    nested = tmp_path / "nested"
    nested.mkdir()
    one = nested / "one.MHTML"
    one.write_bytes(make_mhtml("<table><tr><th>A</th></tr><tr><td>1</td></tr></table>"))
    (nested / "ignore.txt").write_text("ignore", encoding="utf-8")
    assert batch_module.discover_mhtml_files(one) == [one]
    assert batch_module.discover_mhtml_files(tmp_path, recursive=False) == []
    assert batch_module.discover_mhtml_files(tmp_path) == [one]
    assert batch_module.discover_mhtml_files(str(nested / "*.MHTML")) == [one]
    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(nested)
        assert batch_module.discover_mhtml_files("*.MHTML") == [Path("one.MHTML")]
    finally:
        os.chdir(old_cwd)
    assert batch_module.discover_mhtml_files(str(tmp_path / "absent" / "*.mhtml")) == []
    assert batch_module.BatchReport("safe", 0).to_dict()["source"] == "safe"

    class RollbackSink:
        def __init__(self, rollback_error: bool = False) -> None:
            self.rollback_error = rollback_error
            self.rollback_calls = 0

        def rollback(self) -> None:
            self.rollback_calls += 1
            if self.rollback_error:
                raise RuntimeError("connection closed")

    success = {
        "source_sha256": "a" * 64,
        "data_row_count": 2,
        "inserted_rows": 2,
        "skipped": False,
        "table_name": "safe_rows",
    }
    files = [one, nested / "bad.MHTML"]
    (nested / "bad.MHTML").write_bytes(b"not mhtml")
    sink = RollbackSink()
    def fake_convert(path, **kwargs):
        if Path(path).name == "bad.MHTML":
            raise ValueError("private operator path")
        return success

    with patch.object(batch_module, "convert_mhtml_to_postgres", side_effect=fake_convert), patch.object(
        batch_module, "discover_mhtml_files", return_value=files
    ):
        report = batch_module.run_batch(nested, sink=sink, limit=0)
        assert report.files_discovered == 0
        report = batch_module.run_batch(nested, sink=sink)
    assert report.failure_count == 1
    assert report.results[1].error == "ValueError"
    assert str(nested) not in json.dumps(report.to_dict())
    assert sink.rollback_calls == 1

    rollback_error_sink = RollbackSink(rollback_error=True)
    with patch.object(batch_module, "convert_mhtml_to_postgres", side_effect=fake_convert), patch.object(
        batch_module, "discover_mhtml_files", return_value=files
    ):
        failed_report = batch_module.run_batch(nested, sink=rollback_error_sink)
    assert "rollback_failed=RuntimeError" in failed_report.results[1].error

    with patch.object(batch_module, "convert_mhtml_to_postgres", side_effect=fake_convert), patch.object(
        batch_module, "discover_mhtml_files", return_value=files
    ), pytest.raises(batch_module.BatchError, match="batch ingestion failed"):
        batch_module.run_batch(nested, sink=sink, continue_on_error=False)


def test_batch_owns_and_closes_a_postgres_sink(tmp_path: Path) -> None:
    """The batch boundary closes a sink that it created from a DSN."""
    source = tmp_path / "one.MHTML"
    source.write_bytes(b"unused")

    class FakeSink:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_sink = FakeSink()
    result = {
        "source_sha256": "b" * 64,
        "data_row_count": 1,
        "inserted_rows": 1,
        "skipped": False,
        "table_name": "batch_rows",
    }
    with patch("mhtml_etl_gateway.postgres_loader.PsycopgSink", return_value=fake_sink), patch.object(
        batch_module, "convert_mhtml_to_postgres", return_value=result
    ), patch.object(batch_module, "discover_mhtml_files", return_value=[source]):
        report = batch_module.run_batch(tmp_path, dsn="postgresql://redacted")
    assert report.success_count == 1
    assert fake_sink.closed

    class NoCloseSink:
        pass

    with patch("mhtml_etl_gateway.postgres_loader.PsycopgSink", return_value=NoCloseSink()), patch.object(
        batch_module, "convert_mhtml_to_postgres", return_value=result
    ), patch.object(batch_module, "discover_mhtml_files", return_value=[source]):
        assert batch_module.run_batch(tmp_path, dsn="postgresql://redacted").success_count == 1


def test_cli_load_batch_and_summary_contracts(tmp_path: Path, sample_mhtml_path: Path) -> None:
    """Load and batch commands expose only aggregate, privacy-safe result fields."""
    assert cli_module._parse_required_headers(None) is None
    assert cli_module._parse_required_headers("") == []
    assert cli_module._parse_required_headers("NONE") == []
    assert cli_module._parse_required_headers(" A, B ") == ["A", "B"]
    assert cli_module._safe_load_summary({"queryable": "not-a-map", "lineage": []})["artifact_ref"] is None

    source = tmp_path / "source.MHTML"
    source.write_bytes(sample_mhtml_path.read_bytes())
    stderr = StringIO()
    with redirect_stderr(stderr):
        assert cli_module.main(["load", str(tmp_path / "missing.MHTML"), "--dry-run"]) == 2
    assert "unavailable" in stderr.getvalue()
    stderr = StringIO()
    with redirect_stderr(stderr):
        assert cli_module.main(["load", str(source)]) == 2
    assert "DSN" in stderr.getvalue()

    ddl_path = tmp_path / "output.sql"
    lineage_path = tmp_path / "load-lineage.json"
    stdout = StringIO()
    with redirect_stdout(stdout):
        assert cli_module.main(
            [
                "load",
                str(source),
                "--dry-run",
                "--json",
                "--ddl-out",
                str(ddl_path),
                "--lineage-json",
                str(lineage_path),
                "--required-headers",
                "none",
            ]
        ) == 0
    load_summary = json.loads(stdout.getvalue())
    assert load_summary["artifact_ref"].startswith("artifact:")
    assert ddl_path.is_file()
    assert lineage_path.is_file()
    assert str(source) not in stdout.getvalue()

    stdout = StringIO()
    with redirect_stdout(stdout):
        assert cli_module.main(["load", str(source), "--dry-run"]) == 0
    assert "artifact_ref:" in stdout.getvalue()

    with patch.object(cli_module, "convert_mhtml_to_postgres", side_effect=RuntimeError("private")):
        with redirect_stderr(stderr := StringIO()):
            assert cli_module.main(["load", str(source), "--dry-run"]) == 1
    assert "artifact load failed" in stderr.getvalue()

    stderr = StringIO()
    with redirect_stderr(stderr):
        assert cli_module.main(["batch", "--dry-run", "--json"]) == 2
    assert "source is required" in stderr.getvalue()

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "one.MHTML").write_bytes(sample_mhtml_path.read_bytes())
    stderr = StringIO()
    with redirect_stderr(stderr):
        assert cli_module.main(["batch", str(corpus)]) == 2
    assert "DSN" in stderr.getvalue()
    stdout = StringIO()
    with redirect_stdout(stdout):
        assert cli_module.main(["batch", str(corpus), "--dry-run", "--json"]) == 0
    assert json.loads(stdout.getvalue())["success_count"] == 1

    stdout = StringIO()
    with redirect_stdout(stdout):
        assert cli_module.main(["batch", str(corpus), "--dry-run"]) == 0
    assert "discovered:" in stdout.getvalue()

    with patch.object(cli_module, "run_batch", side_effect=RuntimeError("private")):
        with redirect_stderr(stderr := StringIO()):
            assert cli_module.main(["batch", str(corpus), "--dry-run"]) == 1
    assert "batch load failed" in stderr.getvalue()

    failed_report = batch_module.BatchReport("safe", 1, failure_count=1)
    with patch.object(cli_module, "run_batch", return_value=failed_report):
        with redirect_stdout(StringIO()) as output:
            assert cli_module.main(["batch", str(corpus), "--dry-run"]) == 1
    assert "failure_count" in output.getvalue()

    class UnknownParser:
        def parse_args(self, arguments):
            return argparse.Namespace(command="unknown")

    with patch.object(cli_module, "_build_parser", return_value=UnknownParser()), redirect_stderr(
        stderr := StringIO()
    ):
        assert cli_module.main([]) == 2
    assert "invalid_argument" in stderr.getvalue()


def test_postgres_sink_sql_and_transaction_contracts() -> None:
    """The live sink binds values, validates identifiers, and rolls back failures."""

    class Copy:
        def __init__(self, connection, query) -> None:
            self.connection = connection
            self.query = query

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> None:
            return None

        def write_row(self, row) -> None:
            self.connection.calls.append(("copy", self.query, tuple(row)))
            if self.connection.fail_copy:
                raise RuntimeError("copy failed")

    class Cursor:
        def __init__(self, connection) -> None:
            self.connection = connection

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> None:
            return None

        def execute(self, query, params=None) -> None:
            self.connection.calls.append(("execute", query, params))
            if self.connection.fail_execute:
                raise RuntimeError("execute failed")

        def copy(self, query):
            return Copy(self.connection, query)

        def fetchone(self):
            return self.connection.fetchone_result

        def fetchall(self):
            return list(self.connection.fetchall_result)

    class Connection:
        def __init__(self) -> None:
            self.autocommit = True
            self.calls: list[tuple[object, ...]] = []
            self.commits = 0
            self.rollbacks = 0
            self.closed = False
            self.fetchone_result = None
            self.fetchall_result: list[tuple[object, ...]] = []
            self.fail_execute = False
            self.fail_copy = False
            self.fail_rollback = False

        def cursor(self):
            return Cursor(self)

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1
            if self.fail_rollback:
                raise RuntimeError("rollback failed")

        def close(self) -> None:
            self.closed = True

    connection = Connection()
    with patch("psycopg.connect", return_value=connection):
        sink = PsycopgSink("postgresql://example")
    assert connection.autocommit is False
    sink._execute("SELECT 1")
    sink._execute("SELECT %s", (1,))
    sink._copy_rows("COPY rows (value_field) FROM STDIN", [(1,), (2,)])
    assert [call[0] for call in connection.calls].count("copy") == 2
    connection.fetchone_result = (1,)
    assert sink._fetchone("SELECT 1")[0] == 1
    assert sink._fetchone("SELECT %s", (1,))[0] == 1
    connection.fetchall_result = [("a",), ("b",)]
    assert sink._fetchall("SELECT") == [("a",), ("b",)]
    assert sink._fetchall("SELECT %s", (1,)) == [("a",), ("b",)]

    connection.fail_execute = True
    with pytest.raises(LoadError, match="database operation failed"):
        sink._execute("SELECT secret")
    with pytest.raises(LoadError, match="database operation failed"):
        sink._fetchone("SELECT secret")
    with pytest.raises(LoadError, match="database operation failed"):
        sink._fetchall("SELECT secret")
    connection.fail_execute = False
    connection.fail_copy = True
    with pytest.raises(LoadError, match="database operation failed"):
        sink._copy_rows("COPY rows (value_field) FROM STDIN", [("secret",)])
    connection.fail_copy = False

    sink.rollback()
    assert connection.rollbacks == 1
    assert sink.__enter__() is sink
    sink.__exit__(None, None, None)
    assert connection.closed

    with patch("psycopg.connect", side_effect=RuntimeError("secret DSN details")):
        with pytest.raises(LoadError, match="database connection failed") as error:
            PsycopgSink("postgresql://secret")
    assert "secret DSN details" not in str(error.value)

    connection = Connection()
    sink = object.__new__(PsycopgSink)
    sink._conn = connection
    schema = TableSchema(
        table_name="mapped_rows",
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT, comment="business value")],
    )
    connection.fetchall_result = [("value_field", "text")]
    sink.ensure_table(schema)
    sink.ensure_catalog()
    assert connection.commits == 2
    assert any("load_status_code" in str(query) for _, query, _ in connection.calls)
    assert any(
        "RENAME COLUMN status TO load_status_code" in str(query)
        for _, query, _ in connection.calls
    )
    connection.fetchone_result = None
    assert sink.catalog_get("a" * 64, "mapped_rows") is None
    connection.fetchone_result = ("a" * 64, "mapped_rows", "artifact:aaaaaaaaaaaaaaaa", 1, 1, "loaded", None)
    entry = sink.catalog_get("a" * 64, "mapped_rows")
    assert entry is not None and entry.row_count == 1
    connection.fetchone_result = (7,)
    assert sink.count_rows("mapped_rows") == 7
    connection.fetchone_result = None
    assert sink.count_rows("mapped_rows") == 0
    connection.fetchone_result = (3,)
    assert sink.query_count("mapped_rows") == 3
    connection.fetchall_result = [("sample",)]
    assert sink.query_sample("mapped_rows", limit=1) == [("sample",)]

    connection.fetchall_result = []
    unsupported_schema = TableSchema(
        table_name="mapped_rows",
        columns=[ColumnSpec("VALUE", "value_field", "UNSUPPORTED")],
    )
    with pytest.raises(LoadError, match="unsupported schema"):
        sink._ensure_missing_columns(unsupported_schema)

    connection.fetchall_result = [
        ("mixed_value", "bigint"),
        ("already_text", "text"),
        ("compatible_value", "bigint"),
        ("bad_value", "bigint"),
    ]
    promotion_schema = TableSchema(
        table_name="mapped_rows",
        columns=[
            ColumnSpec("MIXED", "mixed_value", PG_TEXT),
            ColumnSpec("TEXT", "already_text", PG_BIGINT),
            ColumnSpec("GOOD", "compatible_value", PG_BIGINT),
            ColumnSpec("BAD", "bad_value", PG_BIGINT),
            ColumnSpec("NEW", "new_value", PG_DATE),
        ],
    )
    assert sink._columns_to_promote(
        promotion_schema, [["x", "1", "2", "bad", None]]
    ) == ["mixed_value", "bad_value"]

    write_connection = Connection()
    write_sink = object.__new__(PsycopgSink)
    write_sink._conn = write_connection
    write_sink._columns_to_promote = lambda schema, rows: ["value_field"]
    catalog_entry = make_catalog_entry(
        sha256="a" * 64,
        table_name="mapped_rows",
        path="artifact:aaaaaaaaaaaaaaaa",
        size=1,
        row_count=1,
    )
    assert write_sink.write_artifact_rows(
        schema,
        [["x"]],
        source_artifact_path="artifact:aaaaaaaaaaaaaaaa",
        source_artifact_sha256="a" * 64,
        catalog_entry=catalog_entry,
        replace_existing=True,
        start_row_number=4,
    ) == 1
    assert write_connection.commits == 1
    copy_calls = [call for call in write_connection.calls if call[0] == "copy"]
    assert len(copy_calls) == 1
    assert "COPY" in str(copy_calls[0][1])
    assert "source_artifact_sha256" in str(copy_calls[0][1])
    write_sink._columns_to_promote = lambda schema, rows: []
    assert write_sink.write_artifact_rows(
        schema,
        [[1]],
        source_artifact_path="artifact:aaaaaaaaaaaaaaaa",
        source_artifact_sha256="a" * 64,
        catalog_entry=catalog_entry,
        replace_existing=False,
    ) == 1
    assert write_sink.write_artifact_rows(
        schema,
        [],
        source_artifact_path="artifact:aaaaaaaaaaaaaaaa",
        source_artifact_sha256="a" * 64,
        catalog_entry=catalog_entry,
        replace_existing=False,
    ) == 0

    failing_connection = Connection()
    failing_connection.fail_copy = True
    failing_sink = object.__new__(PsycopgSink)
    failing_sink._conn = failing_connection
    failing_sink._columns_to_promote = lambda schema, rows: []
    with pytest.raises(LoadError, match="database load failed") as error:
        failing_sink.write_artifact_rows(
            schema,
            [["x"]],
            source_artifact_path="artifact:aaaaaaaaaaaaaaaa",
            source_artifact_sha256="a" * 64,
            catalog_entry=catalog_entry,
            replace_existing=False,
        )
    assert "copy failed" not in str(error.value)
    assert failing_connection.rollbacks == 1

    rollback_failure_connection = Connection()
    rollback_failure_connection.fail_copy = True
    rollback_failure_connection.fail_rollback = True
    rollback_failure_sink = object.__new__(PsycopgSink)
    rollback_failure_sink._conn = rollback_failure_connection
    rollback_failure_sink._columns_to_promote = lambda schema, rows: []
    with pytest.raises(LoadError, match="database load failed"):
        rollback_failure_sink.write_artifact_rows(
            schema,
            [["x"]],
            source_artifact_path="artifact:aaaaaaaaaaaaaaaa",
            source_artifact_sha256="a" * 64,
            catalog_entry=catalog_entry,
            replace_existing=False,
        )
    assert rollback_failure_connection.rollbacks == 1


def test_inmemory_sink_and_load_edge_contracts() -> None:
    """The injectable sink preserves atomic state and rejects invalid digests."""
    schema = TableSchema(
        table_name="edge_rows",
        columns=[ColumnSpec("VALUE", "value_field", PG_TEXT)],
    )
    sink = InMemorySink()
    entry = make_catalog_entry(
        sha256="c" * 64,
        table_name="edge_rows",
        path="artifact:cccccccccccccccc",
        size=1,
        row_count=1,
    )
    with pytest.raises(LoadError, match="not ensured"):
        sink.write_artifact_rows(
            schema,
            [["x"]],
            source_artifact_path=entry.source_artifact_path,
            source_artifact_sha256=entry.source_artifact_sha256,
            catalog_entry=entry,
            replace_existing=False,
        )
    sink.ensure_table(schema)
    sink.catalog[(entry.source_artifact_sha256, entry.table_name)] = entry
    sink.fail_after_delete = True
    with pytest.raises(LoadError):
        sink.write_artifact_rows(
            schema,
            [["new"]],
            source_artifact_path=entry.source_artifact_path,
            source_artifact_sha256=entry.source_artifact_sha256,
            catalog_entry=entry,
            replace_existing=True,
        )
    assert sink.catalog[(entry.source_artifact_sha256, entry.table_name)] == entry
    missing_catalog_entry = make_catalog_entry(
        sha256="e" * 64,
        table_name="edge_rows",
        path="artifact:eeeeeeeeeeeeeeee",
        size=1,
        row_count=1,
    )
    with pytest.raises(LoadError):
        sink.write_artifact_rows(
            schema,
            [["new"]],
            source_artifact_path=missing_catalog_entry.source_artifact_path,
            source_artifact_sha256=missing_catalog_entry.source_artifact_sha256,
            catalog_entry=missing_catalog_entry,
            replace_existing=True,
        )
    assert sink.catalog.get(("e" * 64, "edge_rows")) is None
    assert prepare_typed_rows(schema, [[], ["value"]]) == [[None], ["value"]]

    with pytest.raises(LoadError, match="invalid source"):
        load_table(
            schema,
            [["x"]],
            sink=InMemorySink(),
            source_artifact_path="artifact:bad",
            source_artifact_sha256="bad",
        )
    valid_ref = "artifact:" + "d" * 16
    first_sink = InMemorySink()
    load_table(
        schema,
        [["first"]],
        sink=first_sink,
        source_artifact_path=valid_ref,
        source_artifact_sha256="d" * 64,
    )
    # Defensive handling for a caller outside the Literal type contract.
    load_table(  # type: ignore[arg-type]
        schema,
        [["second"]],
        sink=first_sink,
        source_artifact_path=valid_ref,
        source_artifact_sha256="d" * 64,
        on_duplicate="unexpected",
    )


def test_pipeline_data_mapping_and_sink_variants(tmp_path: Path, sample_mhtml_path: Path) -> None:
    """The pipeline accepts pre-read bytes and keeps sink-specific output bounded."""
    data = sample_mhtml_path.read_bytes()
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(
        json.dumps({"columns": [{"source": "MANDT", "comment": "client identifier"}]}),
        encoding="utf-8",
    )
    extracted = pipeline_module.extract_table(tmp_path / "memory.MHTML", data=data)
    assert extracted.source_size == len(data)
    assert pipeline_module.infer_schema_for_extract(extracted).table_name == "mhtml_extracted_rows"
    result = pipeline_module.convert_mhtml_to_postgres(
        tmp_path / "memory.MHTML",
        data=data,
        sink=InMemorySink(),
        column_mapping=mapping_path,
    )
    assert result["column_comments"]["mandt_field"] == "client identifier"
    assert result["column_mapping"]["matched_count"] == 1

    class GenericSink:
        def __init__(self) -> None:
            self.inner = InMemorySink()

        def ensure_catalog(self) -> None:
            self.inner.ensure_catalog()

        def ensure_table(self, schema) -> None:
            self.inner.ensure_table(schema)

        def catalog_get(self, sha256, table_name):
            return self.inner.catalog_get(sha256, table_name)

        def count_rows(self, table_name):
            return self.inner.count_rows(table_name)

        def write_artifact_rows(self, schema, rows, **kwargs):
            return self.inner.write_artifact_rows(schema, rows, **kwargs)

    generic_result = pipeline_module.convert_mhtml_to_postgres(
        tmp_path / "generic.MHTML",
        data=data,
        sink=GenericSink(),
    )
    assert "sample" not in generic_result["queryable"]

    class FakePsycopgSink(PsycopgSink):
        last = None

        def __init__(self, conninfo: str) -> None:
            class StubConnection:
                autocommit = False

            with patch("psycopg.connect", return_value=StubConnection()):
                super().__init__(conninfo)
            self.inner = InMemorySink()
            self.closed = False
            type(self).last = self

        def ensure_catalog(self) -> None:
            self.inner.ensure_catalog()

        def ensure_table(self, schema) -> None:
            self.inner.ensure_table(schema)

        def catalog_get(self, sha256, table_name):
            return self.inner.catalog_get(sha256, table_name)

        def count_rows(self, table_name):
            return self.inner.count_rows(table_name)

        def write_artifact_rows(self, schema, rows, **kwargs):
            return self.inner.write_artifact_rows(schema, rows, **kwargs)

        def query_sample(self, table_name, limit=3):
            return [("opaque-sample",)]

        def close(self) -> None:
            self.closed = True

    with patch.object(pipeline_module, "PsycopgSink", FakePsycopgSink):
        postgres_result = pipeline_module.convert_mhtml_to_postgres(
            tmp_path / "live.MHTML",
            data=data,
            dsn="postgresql://example",
        )
    assert postgres_result["queryable"]["sample"] == [["opaque-sample"]]
    assert FakePsycopgSink.last is not None and FakePsycopgSink.last.closed


def test_validation_and_identifier_contracts() -> None:
    """Required headers, ragged rows, and database identifiers fail closed."""
    assert is_zcrht811_shaped([], table_name="zcrht811_rows")
    assert is_zcrht811_shaped(["MANDT"])
    assert is_zcrht811_shaped(["GUID"])
    assert is_zcrht811_shaped(["DOCNOSUB", "ACTHGUID"])
    assert not is_zcrht811_shaped(["ordinary"])
    assert resolve_required_headers(["A"], required_headers=[]) == ()
    assert resolve_required_headers(["MANDT", "GUID"]) == DEFAULT_REQUIRED_HEADERS
    assert resolve_required_headers(["A"]) == ()
    valid = validate_extracted_table([" A ", ""], [["1", "2"]], required_headers=[])
    assert valid.messages == ("blank header name(s) present",)
    assert validate_extracted_table(["A"], [], required_headers=[], require_data_rows=False).ok
    assert validate_extracted_table(["A"], [["1", "2"]], required_headers=[], allow_ragged=True).ok
    with pytest.raises(ValidationError, match="no headers"):
        validate_extracted_table([], [])
    with pytest.raises(ValidationError, match="no headers"):
        validate_extracted_table(["", ""], [])
    with pytest.raises(ValidationError, match="missing required"):
        validate_extracted_table(["A"], [["1"]], required_headers=["B"])
    with pytest.raises(ValidationError, match="has 2 cells"):
        validate_extracted_table(["A"], [["1", "2"]], required_headers=[])

    assert require_safe_ident("multiword_name") == "multiword_name"
    valid_maximum = "a" * 30 + "_" + "b" * 32
    assert require_safe_ident(valid_maximum) == valid_maximum
    with pytest.raises(UnsafeIdentifierError):
        require_safe_ident("one-word")
    with pytest.raises(UnsafeIdentifierError):
        require_safe_ident("A")
    with pytest.raises(UnsafeIdentifierError):
        require_safe_ident("a" * 64)
    with pytest.raises(UnsafeIdentifierError) as unsafe_error:
        require_safe_ident("secret_customer_identifier-unsafe")
    assert "secret_customer_identifier-unsafe" not in str(unsafe_error.value)
    with pytest.raises(SchemaInferenceError, match="unsupported PostgreSQL"):
        TableSchema(
            table_name="safe_table",
            columns=[ColumnSpec("VALUE", "value_field", "DROP TABLE")],
        ).ddl()
    assert quote_sql_literal("a\\b'c\n") == "E'a\\\\b''c\\n'"
    with pytest.raises(TypeError):
        quote_sql_literal(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="NUL"):
        quote_sql_literal("bad\x00value")


def test_schema_inference_and_coercion_contracts() -> None:
    """All supported source representations map to predictable PostgreSQL values."""
    for bad in (None, "", "!!!"):
        with pytest.raises(SchemaInferenceError):
            to_snake_case(bad)  # type: ignore[arg-type]
    assert to_snake_case("CamelCase Value") == "camel_case_value"
    long_name = "x" * 63
    assert to_snake_case(long_name).endswith("_field")
    assert len(to_snake_case(long_name)) == 63
    names = unique_snake_names([long_name, long_name, "A", "A_2", "A"])
    assert len(names) == len(set(names))

    assert _parse_int("") is None
    assert _parse_int("+") is None
    assert _parse_int("1,234") == 1234
    assert _parse_int("12,34") is None
    assert _parse_int("-12") == -12
    assert _parse_int("12x") is None
    assert _parse_int("9" * 5000) is None
    assert _parse_decimal("") is None
    assert _parse_decimal("1,234.50") == 1234.50
    assert _parse_decimal("12,34") is None
    assert _parse_decimal("not-a-number") is None

    assert infer_pg_type(["2026-08-11 12:30:00"]) == PG_TIMESTAMP
    assert infer_pg_type(["2026-08-11T12:30:00"]) == PG_TIMESTAMP
    assert infer_pg_type(["2026/08/11 12:30:00"]) == PG_TIMESTAMP
    assert infer_pg_type(["11.08.2026"]) == PG_DATE
    assert infer_pg_type(["12:34:56"]) == PG_TIME
    assert infer_pg_type(["mixed", "1"]) == PG_TEXT
    assert infer_table_schema(["A"], [["1"], []], sample_limit=1).columns[0].pg_type == PG_BIGINT
    simple_schema = infer_table_schema(["A"], [["1"]], table_name="simple_rows")
    assert "source_row_number" not in simple_schema.create_ddl(include_lineage=False)
    assert "COMMENT ON" not in simple_schema.ddl(include_comments=False)
    with pytest.raises(SchemaInferenceError, match="no headers"):
        infer_table_schema([], [])

    assert coerce_value(None, PG_TEXT) is None
    assert coerce_value("", PG_TEXT) is None
    assert coerce_value("YES", PG_BOOLEAN) is True
    assert coerce_value("maybe", PG_BOOLEAN) == "maybe"
    assert coerce_value("1,234", PG_BIGINT) == 1234
    assert coerce_value("bad", PG_BIGINT) == "bad"
    assert coerce_value("1,234.50", PG_NUMERIC) == 1234.50
    assert coerce_value("bad", PG_NUMERIC) == "bad"
    assert coerce_value("20260811", PG_DATE) == date(2026, 8, 11)
    assert coerce_value("bad", PG_DATE) == "bad"
    assert coerce_value("123456", PG_TIME) == time(12, 34, 56)
    assert coerce_value("bad", PG_TIME) == "bad"
    assert coerce_value("2026/08/11 12:30:00", PG_TIMESTAMP) == datetime(2026, 8, 11, 12, 30)
    assert coerce_value("bad", PG_TIMESTAMP) == "bad"
    assert coerce_value("value", "UNKNOWN") == "value"

    assert not values_require_text(PG_TEXT, ["anything"])
    assert not values_require_text(PG_BIGINT, [None, 1])
    assert values_require_text(PG_BIGINT, ["1"])
    assert not values_require_text(PG_NUMERIC, [1, 1.5])
    assert values_require_text(PG_NUMERIC, ["1"])
    assert not values_require_text(PG_BOOLEAN, [True])
    assert values_require_text(PG_BOOLEAN, [1])
    assert not values_require_text(PG_DATE, [date.today()])
    assert values_require_text(PG_DATE, ["2026-01-01"])
    assert not values_require_text(PG_TIME, [time(1, 2)])
    assert values_require_text(PG_TIME, ["01:02"])
    assert not values_require_text(PG_TIMESTAMP, [datetime.now()])
    assert values_require_text(PG_TIMESTAMP, ["now"])
    assert not values_require_text("UNKNOWN", [object()])


def test_column_mapping_fail_closed_and_resolution_edges(tmp_path: Path) -> None:
    """JSON/CSV/PPTX mapping ambiguity and malformed input never silently load."""
    schema = infer_table_schema(
        ["TABLE.ONE", "TABLE.TWO", "TITLE"],
        [["1", "2", "title"]],
        table_name="mapped_rows",
    )
    with pytest.raises(mapping_module.ColumnMappingError, match="source name"):
        mapping_module._normalise_source(" ")
    with pytest.raises(mapping_module.ColumnMappingError, match="missing source"):
        mapping_module._mapping_from_record({"comment": "x"}, location="test")
    with pytest.raises(mapping_module.ColumnMappingError, match="missing comment"):
        mapping_module._mapping_from_record({"source": "A"}, location="test")
    with patch.object(
        mapping_module,
        "_first_value",
        side_effect=["A", " ", None, None],
    ), pytest.raises(mapping_module.ColumnMappingError, match="empty comment"):
        mapping_module._mapping_from_record({"source": "A"}, location="test")
    assert mapping_module._dedupe_mappings([]) == ()
    duplicate = mapping_module.ColumnMapping("A", "same")
    assert mapping_module._dedupe_mappings([duplicate, duplicate]) == (duplicate,)
    assert mapping_module._first_value({"source_name": "X"}, ("missing",)) is None

    assert mapping_module._json_records([{"source": "A", "comment": "x"}])
    with pytest.raises(mapping_module.ColumnMappingError, match="objects"):
        mapping_module._json_records(["bad"])
    with pytest.raises(mapping_module.ColumnMappingError, match="object or array"):
        mapping_module._json_records("bad")
    with pytest.raises(mapping_module.ColumnMappingError, match="array"):
        mapping_module._json_records({"columns": {}})
    assert mapping_module._json_records({"source": "A", "comment": "x"})
    compact = mapping_module._json_records({"TABLE.ONE": {"comment": "x"}, "TABLE.TWO": "y"})
    assert len(compact) == 2

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{", encoding="utf-8")
    with pytest.raises(mapping_module.ColumnMappingError, match="cannot read JSON"):
        mapping_module.load_column_mapping(bad_json)
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]", encoding="utf-8")
    with pytest.raises(mapping_module.ColumnMappingError, match="no mapping records"):
        mapping_module.load_column_mapping(empty_json)
    with pytest.raises(mapping_module.ColumnMappingError, match="not found"):
        mapping_module.load_column_mapping(tmp_path / "missing.json")
    unsupported = tmp_path / "mapping.txt"
    unsupported.write_text("x", encoding="utf-8")
    with pytest.raises(mapping_module.ColumnMappingError, match="unsupported"):
        mapping_module.load_column_mapping(unsupported)

    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")
    with pytest.raises(mapping_module.ColumnMappingError, match="header"):
        mapping_module.load_column_mapping(empty_csv)
    no_rows_csv = tmp_path / "no-rows.csv"
    no_rows_csv.write_text("source,comment\n", encoding="utf-8")
    with pytest.raises(mapping_module.ColumnMappingError, match="no mapping records"):
        mapping_module.load_column_mapping(no_rows_csv)
    with patch.object(Path, "open", side_effect=OSError("private")), pytest.raises(
        mapping_module.ColumnMappingError, match="cannot read CSV"
    ):
        mapping_module._load_csv(no_rows_csv)

    assert mapping_module._xml_texts(
        b"<root><p><t>A</t><t>B</t></p></root>"
    ) == ["AB"]
    assert mapping_module._xml_texts(b"<root><t>fallback</t></root>") == ["fallback"]
    assert mapping_module._xml_texts(b"<root><p><t></t></p><t> </t></root>") == []
    with pytest.raises(mapping_module.ColumnMappingError, match="invalid PPTX"):
        mapping_module._xml_texts(b"<broken")
    assert mapping_module._slide_sources("TABLE.ONE / TWO + ZCRHT999, THREE") == [
        "TABLE.ONE",
        "TABLE.TWO",
        "TABLE.THREE",
    ]
    assert mapping_module._slide_sources("bare table") == []

    no_slide = tmp_path / "no-slide.pptx"
    with zipfile.ZipFile(no_slide, "w") as archive:
        archive.writestr("[Content_Types].xml", "x")
    with pytest.raises(mapping_module.ColumnMappingError, match="no slides"):
        mapping_module.load_column_mapping(no_slide)
    bad_pptx = tmp_path / "bad.pptx"
    bad_pptx.write_bytes(b"not zip")
    with pytest.raises(mapping_module.ColumnMappingError, match="cannot read PPTX"):
        mapping_module.load_column_mapping(bad_pptx)
    no_fields = tmp_path / "no-fields.pptx"
    with zipfile.ZipFile(no_fields, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", "<root><p><t>ordinary</t></p></root>")
    with pytest.raises(mapping_module.ColumnMappingError, match="qualified"):
        mapping_module.load_column_mapping(no_fields)
    duplicate_context = tmp_path / "duplicate-context.pptx"
    with zipfile.ZipFile(duplicate_context, "w") as archive:
        archive.writestr(
            "ppt/slides/slide1.xml",
            "<root><p><t>1. Section</t></p><p><t>TABLE.ONE</t></p>"
            "<p><t>TABLE.ONE</t></p></root>",
        )
    duplicate_doc = mapping_module.load_column_mapping(duplicate_context)
    assert len(duplicate_doc.mappings) == 1

    assert mapping_module._source_candidates(schema, "TABLE.ONE")
    assert mapping_module._source_candidates(schema, "ONE")
    assert mapping_module._source_candidates(schema, "title")
    assert mapping_module._source_candidates(schema, "table_one") == ["table_one"]
    assert mapping_module._source_candidates(schema, ".") == []
    normalized_schema = TableSchema(
        table_name="normalized_rows",
        columns=[ColumnSpec("ORIGINAL", "a_b", PG_TEXT)],
    )
    assert mapping_module._source_candidates(normalized_schema, "A B") == [
        "a_b"
    ]
    assert mapping_module._source_candidates(schema, "not valid !!!") == []
    assert mapping_module._target_candidates(schema, "title_field") == ["title_field"]
    assert mapping_module._target_candidates(schema, "title") == ["title_field"]
    assert mapping_module._target_candidates(schema, "TITLE") == ["title_field"]
    assert mapping_module._target_candidates(schema, "not valid !!!") == []
    assert mapping_module._target_candidates(schema, "!!!") == []

    doc = mapping_module.ColumnMappingDocument(
        path="artifact:" + "c" * 16,
        format="json",
        mappings=(
            mapping_module.ColumnMapping("TABLE.ONE", "one"),
            mapping_module.ColumnMapping("missing", "missing"),
        ),
    )
    commented, report = mapping_module.attach_column_comments(schema, doc)
    assert report.unmatched == ("missing",)
    assert commented.comment_map()["table_one"] == "one"
    duplicate_unmatched = mapping_module.ColumnMappingDocument(
        path=doc.path,
        format="json",
        mappings=(
            mapping_module.ColumnMapping("missing", "one"),
            mapping_module.ColumnMapping("missing", "two"),
        ),
    )
    _, duplicate_report = mapping_module.attach_column_comments(schema, duplicate_unmatched)
    assert duplicate_report.unmatched == ("missing",)
    ambiguous_schema = infer_table_schema(
        ["A.ONE", "B.ONE"], [["1", "2"]], table_name="ambiguous_rows"
    )
    ambiguous = mapping_module.ColumnMappingDocument(
        path=doc.path,
        format="json",
        mappings=(mapping_module.ColumnMapping("ONE", "ambiguous"),),
    )
    with pytest.raises(mapping_module.ColumnMappingError, match="ambiguous"):
        mapping_module.attach_column_comments(ambiguous_schema, ambiguous)
    conflict = mapping_module.ColumnMappingDocument(
        path=doc.path,
        format="json",
        mappings=(
            mapping_module.ColumnMapping("TITLE", "first"),
            mapping_module.ColumnMapping("TITLE", "second"),
        ),
    )
    with pytest.raises(mapping_module.ColumnMappingError, match="conflicting"):
        mapping_module.attach_column_comments(schema, conflict)
    pptx_conflict = mapping_module.ColumnMappingDocument(
        path=doc.path,
        format="pptx",
        mappings=conflict.mappings,
    )
    merged, _ = mapping_module.attach_column_comments(schema, pptx_conflict)
    assert merged.comment_map()["title_field"] == "first; second"


def test_mapping_reference_handles_unreadable_artifact(tmp_path: Path) -> None:
    """Unreadable mapping bytes are reported without leaking the source path."""
    path = tmp_path / "mapping.json"
    path.write_text("{}", encoding="utf-8")
    with patch.object(Path, "read_bytes", side_effect=OSError("private")), pytest.raises(
        mapping_module.ColumnMappingError, match="fingerprint"
    ):
        mapping_module._mapping_reference(path)
