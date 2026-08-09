"""Contract tests for deterministic, value-free schema proposals."""

from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import mhtml_etl_gateway.schema_proposal as module
import mhtml_etl_gateway.schema_proposal.naming as naming
from mhtml_etl_gateway.schema_proposal import (
    ColumnEvidence,
    ColumnProposal,
    SchemaProposal,
    SchemaProposalPolicy,
    propose_postgresql_schema,
)


class SchemaProposalContractTests(unittest.TestCase):
    """Verify naming, ordering, content identity, and value-free serialization."""

    def test_sap_shaped_proposal_is_ordered_and_value_free(self) -> None:
        """Representative SAP columns retain identity semantics without raw values."""
        columns = (
            ColumnEvidence("MANDT", ("100", "200")),
            ColumnEvidence("GUID", ("01987f4a-cc11-7c77-8d88-123456789abc",)),
            ColumnEvidence("DOCNOSUB", ("0001", "0002")),
            ColumnEvidence("DUEDT", ("20250131", "20250201")),
            ColumnEvidence("KUNNR", ("0012345678", "0098765432")),
            ColumnEvidence("고객 이름", ("김민수", "박지영")),
        )
        proposal = propose_postgresql_schema("SAP Inspection Export", columns)
        self.assertEqual(proposal.target_table_name, "sap_inspection_export")
        self.assertEqual(
            [column.target_column_name for column in proposal.columns],
            [
                "client_code",
                "global_identifier",
                "document_subnumber",
                "due_date",
                "customer_number",
                "고객_이름",
            ],
        )
        self.assertEqual(
            [column.proposed_postgresql_type for column in proposal.columns],
            ["text", "text", "text", "date", "text", "text"],
        )
        rendered = json.dumps(proposal.to_dict(), ensure_ascii=False, sort_keys=True)
        for protected in (
            "MANDT",
            "GUID",
            "DOCNOSUB",
            "DUEDT",
            "KUNNR",
            "김민수",
            "박지영",
            "0012345678",
            "20250131",
        ):
            self.assertNotIn(protected, rendered)

    def test_names_are_multiword_snake_case_unique_reserved_safe_and_bounded(self) -> None:
        """Names remain deterministic under aliases, collisions, Unicode, and limits."""
        policy = SchemaProposalPolicy(max_identifier_bytes=24)
        proposal = propose_postgresql_schema(
            "Table",
            (
                ColumnEvidence("metricValue", ("1",)),
                ColumnEvidence("metric value", ("2",)),
                ColumnEvidence("select", ("x",)),
                ColumnEvidence("제목", ("y",)),
                ColumnEvidence("A" * 100, ("z",)),
                ColumnEvidence("!!!", ("fallback",)),
            ),
            policy=policy,
        )
        names = [item.target_column_name for item in proposal.columns]
        self.assertEqual(proposal.target_table_name, "table_record")
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[0], "metric_value")
        self.assertRegex(names[1], r"^metric_value_[0-9a-f]{10}$")
        self.assertEqual(names[2], "select_column")
        self.assertEqual(names[3], "제목_column")
        self.assertEqual(names[5], "source_column")
        for name in names:
            self.assertIn("_", name)
            self.assertLessEqual(len(name.encode("utf-8")), 24)
            self.assertRegex(name, r"^\w+(?:_\w+)+$")

    def test_duplicate_identical_headers_receive_stable_nonordinal_names(self) -> None:
        """Repeated identical headers resolve through content-derived suffixes."""
        columns = (
            ColumnEvidence("Value", (1,)),
            ColumnEvidence("Value", (2,)),
            ColumnEvidence("Value", (3,)),
        )
        first = propose_postgresql_schema("Repeated Headers", columns)
        second = propose_postgresql_schema("Repeated Headers", columns)
        names = [item.target_column_name for item in first.columns]
        self.assertEqual(first, second)
        self.assertEqual(names[0], "value_column")
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(not re.search(r"_\d+$", name) for name in names[1:]))

    def test_identity_changes_with_order_values_or_policy_but_is_repeatable(self) -> None:
        """Content addresses bind ordered evidence and complete policy state."""
        columns = (
            ColumnEvidence("first_value", (1, 2)),
            ColumnEvidence("second_value", (3, 4)),
        )
        first = propose_postgresql_schema("Metrics", columns)
        repeat = propose_postgresql_schema("Metrics", columns)
        reordered = propose_postgresql_schema("Metrics", tuple(reversed(columns)))
        changed_value = propose_postgresql_schema(
            "Metrics",
            (columns[0], ColumnEvidence("second_value", (3, 5))),
        )
        changed_policy = propose_postgresql_schema(
            "Metrics",
            columns,
            policy=SchemaProposalPolicy(policy_version="default/2"),
        )
        self.assertEqual(first, repeat)
        self.assertNotEqual(
            first.table_fingerprint_sha256,
            reordered.table_fingerprint_sha256,
        )
        self.assertNotEqual(
            first.proposal_fingerprint_sha256,
            reordered.proposal_fingerprint_sha256,
        )
        self.assertNotEqual(
            first.proposal_fingerprint_sha256,
            changed_value.proposal_fingerprint_sha256,
        )
        self.assertNotEqual(
            first.proposal_fingerprint_sha256,
            changed_policy.proposal_fingerprint_sha256,
        )
        self.assertEqual(
            [item.target_column_name for item in reordered.columns],
            ["second_value", "first_value"],
        )

    def test_serialized_contract_has_only_value_free_fields(self) -> None:
        """Public serialization and repr cannot contain protected input attributes."""
        evidence = ColumnEvidence("Raw Header", ("Raw Value",))
        proposal = propose_postgresql_schema("Protected Report!", (evidence,))
        serialized = proposal.to_dict()
        rendered = json.dumps(serialized, sort_keys=True)
        self.assertNotIn("Protected Report!", rendered)
        self.assertNotIn("Raw Header", rendered)
        self.assertNotIn("Raw Value", rendered)
        self.assertNotIn("header", serialized["columns"][0])
        self.assertNotIn("samples", serialized["columns"][0])
        self.assertEqual(repr(evidence), "ColumnEvidence(protected=True)")
        self.assertNotIn("Raw Header", repr(evidence))
        self.assertNotIn("Raw Value", repr(evidence))
        self.assertEqual(set(serialized), {field.name for field in fields(SchemaProposal)})
        self.assertEqual(
            set(serialized["columns"][0]),
            {field.name for field in fields(ColumnProposal)},
        )

    def test_collision_retry_and_truncation_fallbacks_are_deterministic(self) -> None:
        """Pathological hash collisions and empty prefixes retain bounded names."""
        used = {"value_column", "value_column_deadbeef00"}
        digests = iter(("deadbeef00" + "0" * 54, "cafebabe00" + "0" * 54))
        with patch.object(naming, "sha256_text", side_effect=lambda _: next(digests)):
            resolved = naming.unique_column_name(
                "value_column",
                "a" * 64,
                used,
                63,
            )
        self.assertEqual(resolved, "value_column_cafebabe00")

        with patch.object(naming, "sha256_text", return_value="a" * 64):
            truncated = naming.truncate_identifier("_" * 20, 16, "seed")
        self.assertLessEqual(len(truncated.encode("utf-8")), 16)
        self.assertRegex(truncated, r"_[0-9a-f]{10}$")

    def test_module_performs_no_ddl_network_database_or_file_io(self) -> None:
        """Production source contains no persistence or transport capability."""
        package_root = Path(module.__file__).resolve().parent
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(package_root.glob("*.py"))
        )
        prohibited = (
            "CREATE TABLE",
            "ALTER TABLE",
            "DROP TABLE",
            "socket.",
            "requests.",
            "urllib.request",
            "psycopg",
            "sqlalchemy",
            "open(",
            "Path(",
        )
        production = text.split("__all__", 1)[0]
        for fragment in prohibited:
            self.assertNotIn(fragment, production)


if __name__ == "__main__":
    unittest.main()
