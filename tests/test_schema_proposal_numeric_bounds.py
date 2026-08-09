"""Numeric and date boundary tests for conservative schema inference."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.schema_proposal import ColumnEvidence, propose_postgresql_schema


class SchemaProposalNumericBoundsTests(unittest.TestCase):
    """Prevent large or non-ASCII numeric syntax from escaping bounded inference."""

    def test_very_long_integer_string_is_classified_without_python_int_conversion(self) -> None:
        """A 5,000-digit integer becomes reviewed numeric evidence without ValueError."""
        proposal = propose_postgresql_schema(
            "Large Integer Evidence",
            (ColumnEvidence("measure_value", ("9" * 5000,)),),
        )
        column = proposal.columns[0]
        self.assertEqual(column.proposed_postgresql_type, "numeric")
        self.assertTrue(column.review_required)
        self.assertIn("integer_outside_int64_range", column.review_reasons)

    def test_huge_exponent_numeric_string_falls_back_to_reviewed_text(self) -> None:
        """Numeric-looking text cannot imply an exponent-sized PostgreSQL value."""
        proposal = propose_postgresql_schema(
            "Exponent Evidence",
            (ColumnEvidence("measure_value", ("1e1000000000",)),),
        )
        column = proposal.columns[0]
        self.assertEqual(column.proposed_postgresql_type, "text")
        self.assertTrue(column.review_required)
        self.assertIn(
            "numeric_value_outside_supported_range",
            column.review_reasons,
        )

    def test_non_ascii_date_digits_do_not_enter_date_inference(self) -> None:
        """Date semantics require ASCII source syntax for configured formats."""
        proposal = propose_postgresql_schema(
            "Unicode Date Evidence",
            (ColumnEvidence("event_date", ("٢٠٢٥٠١٣١",)),),
        )
        column = proposal.columns[0]
        self.assertEqual(column.proposed_postgresql_type, "text")
        self.assertTrue(column.review_required)
        self.assertIn("date_semantics_with_invalid_value", column.review_reasons)


if __name__ == "__main__":
    unittest.main()
