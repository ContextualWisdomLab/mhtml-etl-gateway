"""Focused coverage for defensive and conservative schema-proposal branches."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mhtml_etl_gateway.schema_proposal import (
    PostgresType,
    ProtectedColumnInput,
    SchemaProposalError,
    SchemaProposalErrorCode,
    _fit_identifier,
    _truncate_utf8,
    propose_schema,
)


_SOURCE_HASH = "b" * 64


class SchemaProposalCoverageTests(unittest.TestCase):
    """Exercise branches that ordinary successful proposal inputs rarely reach."""

    def test_utf8_truncation_can_remove_an_incomplete_first_character(self) -> None:
        """A one-byte cut through a two-byte code point returns a valid empty prefix."""
        self.assertEqual(_truncate_utf8("é", 1), "")

    def test_identifier_fitting_uses_source_fallback_for_empty_prefix(self) -> None:
        """A long final token cannot leave the generated identifier prefix empty."""
        fitted = _fit_identifier("_" + "x" * 100)
        self.assertTrue(fitted.startswith("source_"))

    def test_date_shaped_identifier_keeps_both_review_reasons(self) -> None:
        """Date evidence under identifier semantics remains text and fully explained."""
        column = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput(
                    "accountDate",
                    ("2025-01-31",),
                    complete=True,
                ),
            ),
        ).columns[0]
        self.assertEqual(column.proposed_type, PostgresType.TEXT)
        self.assertEqual(
            column.review_reasons,
            ("identifier_semantics", "date_semantics_missing"),
        )

    def test_date_shaped_value_without_semantics_has_one_review_reason(self) -> None:
        """A date-shaped metric remains text without invented date or ID meaning."""
        column = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput(
                    "metricValue",
                    ("2025-01-31",),
                    complete=True,
                ),
            ),
        ).columns[0]
        self.assertEqual(column.proposed_type, PostgresType.TEXT)
        self.assertEqual(column.review_reasons, ("date_semantics_missing",))

    def test_decimal_identifier_and_leading_zero_reasons_are_independent(self) -> None:
        """Fixed-point values preserve identifier and textual-width evidence."""
        proposal = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput(
                    "accountNumber",
                    ("12.50",),
                    complete=True,
                ),
                ProtectedColumnInput(
                    "metricValue",
                    ("01.50",),
                    complete=True,
                ),
            ),
        )
        self.assertEqual(
            proposal.columns[0].review_reasons,
            ("identifier_semantics",),
        )
        self.assertEqual(
            proposal.columns[1].review_reasons,
            ("leading_zero_identifier",),
        )
        self.assertTrue(
            all(
                column.proposed_type is PostgresType.TEXT
                for column in proposal.columns
            )
        )

    def test_non_sequence_and_non_column_items_fail_closed(self) -> None:
        """Generators and foreign objects cannot enter protected proposal processing."""
        invalid_inputs = (
            (item for item in (ProtectedColumnInput("A", ("1",)),)),
            (object(),),
        )
        for columns in invalid_inputs:
            with self.subTest(columns_type=type(columns).__name__):
                with self.assertRaises(SchemaProposalError) as caught:
                    propose_schema(_SOURCE_HASH, columns)  # type: ignore[arg-type]
                self.assertEqual(
                    caught.exception.code,
                    SchemaProposalErrorCode.INVALID_INPUT,
                )

    def test_collision_guard_rejects_a_repeated_opaque_name(self) -> None:
        """A hash collision cannot silently produce duplicate target identifiers."""
        columns = (
            ProtectedColumnInput("Customer Number", ("1",)),
            ProtectedColumnInput("customer-number", ("2",)),
        )
        with patch(
            "mhtml_etl_gateway.schema_proposal._collision_name",
            return_value="customer_number",
        ):
            with self.assertRaises(SchemaProposalError) as caught:
                propose_schema(_SOURCE_HASH, columns)
        self.assertEqual(
            caught.exception.code,
            SchemaProposalErrorCode.INVALID_INPUT,
        )


if __name__ == "__main__":
    unittest.main()
