from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from mhtml_etl_gateway.column_mapping import (
    ColumnMappingError,
    attach_column_comments,
    load_column_mapping,
)
from mhtml_etl_gateway.lineage import artifact_reference, build_lineage, sha256_bytes
from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres
from mhtml_etl_gateway.postgres_loader import PsycopgSink
from mhtml_etl_gateway.schema_inference import TableSchema, infer_table_schema
from mhtml_etl_gateway.sql_ident import quote_sql_literal


def _schema() -> TableSchema:
    return infer_table_schema(
        ["ERDAT", "ERZET", "TITLE"],
        [["2026-08-11", "09:10:11", "VOC title"]],
        table_name="voc_rows",
    )


def test_json_mapping_attaches_comments_by_qualified_source(tmp_path: Path) -> None:
    path = tmp_path / "voc-mapping.json"
    path.write_text(
        json.dumps(
            {
                "columns": [
                    {
                        "source": "ZCRHT810.ERDAT",
                        "comment": "VOC 작성일자",
                    },
                    {
                        "source": "ZCRHT811.TITLE",
                        "target": "title",
                        "description": "상담 제목",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    document = load_column_mapping(path)
    schema, report = attach_column_comments(_schema(), document)

    assert document.path.startswith("artifact:")
    assert str(path) not in document.path
    assert report.matched == {
        "ZCRHT810.ERDAT": "erdat_field",
        "ZCRHT811.TITLE": "title_field",
    }
    assert report.unmatched == ()
    assert schema.comment_map() == {
        "erdat_field": "VOC 작성일자",
        "title_field": "상담 제목",
    }
    assert "COMMENT ON COLUMN voc_rows.erdat_field IS E'VOC 작성일자';" in schema.ddl()
    assert "COMMENT ON COLUMN voc_rows.title_field IS E'상담 제목';" in schema.ddl()


def test_mapping_errors_do_not_include_source_path(tmp_path: Path) -> None:
    path = tmp_path / "private-map.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(ColumnMappingError) as exc_info:
        load_column_mapping(path)

    assert str(path) not in str(exc_info.value)


def test_csv_mapping_and_unmatched_reference_are_reported(tmp_path: Path) -> None:
    path = tmp_path / "voc-mapping.csv"
    path.write_text(
        "source,target,comment\n"
        "ZCRHT823.ERZET,,상담 생성 시간\n"
        "ZCRHT999.MISSING,,다른 화면 필드\n",
        encoding="utf-8",
    )

    schema, report = attach_column_comments(_schema(), load_column_mapping(path))

    assert schema.comment_map() == {"erzet_field": "상담 생성 시간"}
    assert report.matched == {"ZCRHT823.ERZET": "erzet_field"}
    assert report.unmatched == ("ZCRHT999.MISSING",)


def test_pptx_mapping_reads_text_layer_and_expression_suffixes(tmp_path: Path) -> None:
    path = tmp_path / "voc-reference.pptx"
    slide_xml = """\
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
        xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
    <p:sp><p:txBody>
      <a:p><a:r><a:t>3. 상담 내역(상세)</a:t></a:r></a:p>
      <a:p><a:r><a:t>ZCRHT823.ERDAT / ERZET</a:t></a:r></a:p>
      <a:p><a:r><a:t>ZCRHT811.TITLE</a:t></a:r></a:p>
    </p:txBody></p:sp>
  </p:spTree></p:cSld>
</p:sld>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide_xml)

    document = load_column_mapping(path)
    schema, report = attach_column_comments(_schema(), document)

    assert document.path.startswith("artifact:")
    assert all(mapping.slide_number == 1 for mapping in document.mappings)
    assert len(report.matched) == 3
    assert set(report.matched) == {
        "ZCRHT823.ERDAT",
        "ZCRHT823.ERZET",
        "ZCRHT811.TITLE",
    }
    assert all("3. 상담 내역(상세)" in value for value in schema.comment_map().values())


def test_pipeline_result_and_ddl_include_column_comments(
    sample_mhtml_path, tmp_path: Path
) -> None:
    mapping = tmp_path / "mapping.json"
    mapping.write_text(
        json.dumps(
            {
                "MANDT": "클라이언트",
                "ZCRHT811.TITLE": {"target": "title", "comment": "상담 제목"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = convert_mhtml_to_postgres(
        sample_mhtml_path,
        table_name="zcrht811_export_rows",
        column_mapping=mapping,
    )

    assert result["column_comments"] == {
        "mandt_field": "클라이언트",
        "title_field": "상담 제목",
    }
    assert result["column_mapping"]["matched_count"] == 2
    assert result["column_mapping"]["path"].startswith("artifact:")
    assert str(mapping) not in json.dumps(result["column_mapping"], ensure_ascii=False)
    assert "COMMENT ON COLUMN zcrht811_export_rows.mandt_field" in result["ddl"]
    assert "COMMENT ON COLUMN zcrht811_export_rows.title_field" in result["ddl"]


def test_pipeline_redacts_input_path_and_filename_derived_table_name(
    sample_mhtml_path,
) -> None:
    result = convert_mhtml_to_postgres(sample_mhtml_path)
    serialized = json.dumps(result, ensure_ascii=False, default=str)

    assert str(sample_mhtml_path) not in serialized
    assert result["table_name"] == "mhtml_extracted_rows"
    assert result["lineage"]["source_artifact_path"].startswith("artifact:")
    assert "sample" not in result["queryable"]
    assert result["queryable"]["table_name"] == result["table_name"]
    assert result["queryable"]["db_row_count"] == result["inserted_rows"]


def test_artifact_reference_is_opaque_and_validated() -> None:
    digest = "a" * 64
    assert artifact_reference(digest) == "artifact:aaaaaaaaaaaaaaaa"
    with pytest.raises(ValueError, match="64-character"):
        artifact_reference("not-a-digest")


def test_lineage_rejects_non_opaque_explicit_source(tmp_path: Path) -> None:
    data = b"safe-source"
    path = tmp_path / "private.MHTML"
    expected_reference = artifact_reference(sha256_bytes(data))

    lineage = build_lineage(
        path,
        data=data,
        row_count=1,
        table_name="safe_rows",
    )
    assert lineage.source_artifact_path == expected_reference

    with pytest.raises(ValueError, match="does not match"):
        build_lineage(
            path,
            data=data,
            row_count=1,
            table_name="safe_rows",
            source_artifact_path=str(path),
        )


def test_explicit_conflicting_comments_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "conflict.json"
    path.write_text(
        json.dumps(
            [
                {"source": "ERDAT", "comment": "첫 설명"},
                {"source": "ZCRHT810.ERDAT", "comment": "다른 설명"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ColumnMappingError, match="conflicting comments"):
        attach_column_comments(_schema(), load_column_mapping(path))


def test_comment_literal_escapes_sql_syntax_and_rejects_nul() -> None:
    literal = quote_sql_literal("O'Reilly \\ path\nnext")
    assert literal == "E'O''Reilly \\\\ path\\nnext'"
    with pytest.raises(ValueError, match="NUL"):
        quote_sql_literal("bad\x00comment")


def test_live_sink_executes_create_and_comments_separately() -> None:
    class Cursor:
        def __init__(self, calls: list[object]) -> None:
            self.calls = calls

        def __enter__(self) -> "Cursor":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def execute(self, query, params=None) -> None:
            self.calls.append((query, params))

    class Connection:
        def __init__(self) -> None:
            self.calls: list[object] = []
            self.commits = 0

        def cursor(self) -> Cursor:
            return Cursor(self.calls)

        def commit(self) -> None:
            self.commits += 1

    connection = Connection()
    sink = object.__new__(PsycopgSink)
    sink._conn = connection
    schema = _schema().with_column_comments({"title_field": "상담 제목"})
    sink._fetchall = lambda query, params=None: [
        (column.db_name, column.pg_type.lower()) for column in schema.columns
    ]

    sink.ensure_table(schema)

    assert connection.commits == 1
    assert [query for query, _ in connection.calls] == [
        schema.create_ddl(include_lineage=True),
        "COMMENT ON COLUMN voc_rows.title_field IS E'상담 제목';",
    ]
