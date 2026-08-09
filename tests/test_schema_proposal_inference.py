"""Inference tests for conservative PostgreSQL schema proposals."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import unittest

from mhtml_etl_gateway.schema_proposal import (
    ColumnEvidence,
    propose_postgresql_schema,
)


class SchemaProposalInferenceTests(unittest.TestCase):
    """Verify lossless types, ambiguity flags, and identifier preservation."""

    def test_boolean_numeric_null_and_ambiguous_policies_are_conservative(self) -> None:
        """Only complete policy-supported evidence receives a non-text proposal."""
        proposal = propose_postgresql_schema(
            "Quality Metrics",
            (
                ColumnEvidence("active_flag", ("Y", "N", None)),
                ColumnEvidence("record_count", (1, "2", 3)),
                ColumnEvidence("ratio_value", (Decimal("1.25"), "2.50")),
                ColumnEvidence("large_measure", (2**63, str(2**63 + 1))),
                ColumnEvidence("empty_field", (None, "  ")),
                ColumnEvidence("mixed_value", ("alpha", 2)),
                ColumnEvidence("event_date", ("2025-02-30",)),
                ColumnEvidence("binary_ratio", (0.1, 0.2)),
                ColumnEvidence("whole_decimal", (Decimal("12"),)),
            ),
        )
        by_name = {item.target_column_name: item for item in proposal.columns}
        self.assertEqual(by_name["active_flag"].proposed_postgresql_type, "boolean")
        self.assertEqual(by_name["record_count"].proposed_postgresql_type, "bigint")
        self.assertEqual(by_name["ratio_value"].proposed_postgresql_type, "numeric")
        self.assertEqual(by_name["large_measure"].proposed_postgresql_type, "numeric")
        self.assertTrue(by_name["large_measure"].review_required)
        self.assertEqual(by_name["empty_field"].proposed_postgresql_type, "text")
        self.assertEqual(by_name["empty_field"].blank_count, 2)
        self.assertTrue(by_name["empty_field"].review_required)
        self.assertEqual(by_name["mixed_value"].proposed_postgresql_type, "text")
        self.assertTrue(by_name["mixed_value"].review_required)
        self.assertEqual(by_name["event_date"].proposed_postgresql_type, "text")
        self.assertIn(
            "date_semantics_with_invalid_value",
            by_name["event_date"].review_reasons,
        )
        self.assertEqual(by_name["binary_ratio"].proposed_postgresql_type, "numeric")
        self.assertIn(
            "binary_float_requires_review",
            by_name["binary_ratio"].review_reasons,
        )
        self.assertEqual(by_name["whole_decimal"].proposed_postgresql_type, "numeric")

    def test_native_boolean_and_date_objects_avoid_datetime_loss(self) -> None:
        """Native booleans/dates are accepted while datetime-to-date loss is rejected."""
        proposal = propose_postgresql_schema(
            "Object Evidence",
            (
                ColumnEvidence("enabled_flag", (True, False)),
                ColumnEvidence("due_date", (date(2025, 1, 1), date(2025, 1, 2))),
                ColumnEvidence("created_date", (datetime(2025, 1, 1, 8, 30),)),
            ),
        )
        self.assertEqual(
            [item.proposed_postgresql_type for item in proposal.columns],
            ["boolean", "date", "text"],
        )
        self.assertTrue(proposal.columns[2].review_required)

    def test_identifier_semantics_prevent_optimistic_number_conversion(self) -> None:
        """Identifier headers and leading-zero strings remain text."""
        proposal = propose_postgresql_schema(
            "Identifier Evidence",
            (
                ColumnEvidence("accountId", (123, 456)),
                ColumnEvidence("postal_value", ("00101", "90210")),
                ColumnEvidence("regular_value", ("12", "13")),
            ),
        )
        self.assertEqual(
            [item.proposed_postgresql_type for item in proposal.columns],
            ["text", "text", "bigint"],
        )
        self.assertIn("identifier_semantics", proposal.columns[0].evidence_codes)
        self.assertIn("leading_zero_value", proposal.columns[1].evidence_codes)

    def test_unmarked_boolean_words_remain_text(self) -> None:
        """Boolean vocabulary alone is insufficient without boolean semantics."""
        proposal = propose_postgresql_schema(
            "Status Evidence",
            (ColumnEvidence("status_value", ("true", "false")),),
        )
        self.assertEqual(proposal.columns[0].proposed_postgresql_type, "text")
        self.assertFalse(proposal.columns[0].review_required)


if __name__ == "__main__":
    unittest.main()
