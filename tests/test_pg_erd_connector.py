from __future__ import annotations

import json
from dataclasses import replace

import pytest

from mhtml_etl_gateway.pg_erd_connector import (
    PgErdVisualizationPlan,
    build_pg_erd_visualization_plan,
)
from mhtml_etl_gateway.schema_proposal import (
    ColumnProposal,
    ProtectedColumnInput,
    SchemaProposal,
    propose_schema,
)


def _proposal() -> SchemaProposal:
    """Return realistic protected evidence for DBML contract tests."""
    return propose_schema(
        "a" * 64,
        (
            ProtectedColumnInput("MANDT", ("603", "603"), complete=True),
            ProtectedColumnInput("ACTIVE_FLAG", ("true", "false"), complete=True),
            ProtectedColumnInput(
                "EVENT_DATE",
                ("20260220", "20260221"),
                complete=True,
            ),
            ProtectedColumnInput("AMOUNT", ("12.50", "13.00"), complete=True),
            ProtectedColumnInput("ROW_COUNT", ("1", "2"), complete=True),
        ),
    )


def test_plan_matches_pg_erd_dbml_request_and_is_value_free() -> None:
    """Plans use DBML structure and never serialize protected headers or values."""
    plan = build_pg_erd_visualization_plan(
        _proposal(),
        catalog_name="SAP VOC export",
    )
    payload = plan.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert isinstance(plan, PgErdVisualizationPlan)
    assert payload["contract_version"] == "1.0.0"
    assert payload["target_system"] == "pg-erd-cloud"
    assert payload["request"]["method"] == "POST"
    assert payload["request"]["path"] == "/api/dbml/convert"
    assert payload["request"]["body"]["include_ddl"] is False
    assert payload["request"]["body"]["dialect"] == "postgresql"
    assert payload["request"]["body"]["dbml"] == (
        "Table sap_voc_export {\n"
        "  client_code text [not null]\n"
        "  active_flag boolean [not null]\n"
        "  event_date date [not null]\n"
        "  amount_field numeric [not null]\n"
        "  row_count bigint [not null]\n"
        "}"
    )
    assert "MANDT" not in encoded
    assert "603" not in encoded
    assert "20260220" not in encoded
    assert "//" not in payload["request"]["body"]["dbml"]
    assert "note" not in payload["request"]["body"]["dbml"]
    assert "records" not in payload["request"]["body"]["dbml"]
    assert "a" * 64 in encoded


def test_plan_is_deterministic_and_supports_empty_proposal() -> None:
    """Equal proposals produce equal plans, including a valid empty table."""
    proposal = _proposal()
    first = build_pg_erd_visualization_plan(proposal, catalog_name="VOC")
    second = build_pg_erd_visualization_plan(proposal, catalog_name="VOC")
    empty = SchemaProposal(
        schema_proposal_id="schema_proposal_empty",
        proposal_version="1.0.0",
        source_hash_sha256="b" * 64,
        table_fingerprint_sha256="c" * 64,
        columns=(),
    )

    assert first.to_dict() == second.to_dict()
    nullable_proposal = replace(
        proposal,
        columns=(replace(proposal.columns[0], nullable=True),),
    )
    assert build_pg_erd_visualization_plan(
        nullable_proposal,
        catalog_name="VOC",
    ).dbml == "Table voc_table {\n  client_code text\n}"
    assert build_pg_erd_visualization_plan(empty, catalog_name="Empty source").dbml == (
        "Table empty_source {\n\n}"
    )


@pytest.mark.parametrize(
    "catalog_name",
    ["", 42, "--", "bad\nsource"],
)
def test_plan_rejects_unsafe_catalog_names(catalog_name: object) -> None:
    """DBML table names fail closed for malformed or control metadata."""
    with pytest.raises(ValueError, match="catalog_name"):
        build_pg_erd_visualization_plan(  # type: ignore[arg-type]
            _proposal(),
            catalog_name=catalog_name,
        )


def test_plan_rejects_non_proposal_input() -> None:
    """The connector accepts only the established value-free proposal type."""
    with pytest.raises(ValueError, match="proposal"):
        build_pg_erd_visualization_plan(object(), catalog_name="VOC")  # type: ignore[arg-type]


def test_plan_direct_construction_cannot_override_contract() -> None:
    """Plans cannot bypass the builder's value-free fixed request contract."""
    with pytest.raises(TypeError, match="build_pg_erd_visualization_plan"):
        PgErdVisualizationPlan(
            contract_version="attacker-controlled",
            target_system="other-service",
            source_hash_sha256="a" * 64,
            schema_proposal_id="schema_proposal_demo",
            dbml="Table unsafe_table { secret_text text [note: 'raw'] }",
            include_ddl=True,
            dialect="snowflake",
        )


def test_plan_rejects_invalid_column_objects() -> None:
    """Malformed manually constructed proposals cannot reach DBML output."""
    proposal = replace(_proposal(), columns=(object(),))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="invalid column"):
        build_pg_erd_visualization_plan(proposal, catalog_name="VOC")


@pytest.mark.parametrize(
    "column",
    [
        replace(_proposal().columns[0], target_column_name="unsafe-name"),
        replace(_proposal().columns[0], proposed_type="json"),  # type: ignore[arg-type]
        replace(_proposal().columns[0], nullable="no"),  # type: ignore[arg-type]
    ],
)
def test_plan_rejects_invalid_column_definitions(column: ColumnProposal) -> None:
    """Unsafe names, types, and nullability flags are rejected before rendering."""
    proposal = replace(_proposal(), columns=(column,))

    with pytest.raises(
        ValueError,
        match=r"unsafe column definition|nullable flag",
    ):
        build_pg_erd_visualization_plan(proposal, catalog_name="VOC")
