"""Exact decimal identity tests for value-free schema proposals."""

from __future__ import annotations

from decimal import Decimal
import unittest

from mhtml_etl_gateway.schema_proposal import ColumnEvidence, propose_postgresql_schema


class SchemaProposalDecimalIdentityTests(unittest.TestCase):
    """Protect decimal evidence from context rounding and exponent expansion."""

    def test_decimal_identity_distinguishes_digits_beyond_context_precision(self) -> None:
        """Two exact decimals differing after 28 digits produce different identities."""
        left = propose_postgresql_schema(
            "Decimal Evidence",
            (
                ColumnEvidence(
                    "exact_decimal",
                    (Decimal("123456789012345678901234567890"),),
                ),
            ),
        )
        right = propose_postgresql_schema(
            "Decimal Evidence",
            (
                ColumnEvidence(
                    "exact_decimal",
                    (Decimal("123456789012345678901234567891"),),
                ),
            ),
        )
        self.assertNotEqual(
            left.columns[0].evidence_fingerprint_sha256,
            right.columns[0].evidence_fingerprint_sha256,
        )
        self.assertNotEqual(
            left.proposal_fingerprint_sha256,
            right.proposal_fingerprint_sha256,
        )

    def test_equivalent_decimal_encodings_have_one_canonical_identity(self) -> None:
        """Trailing zeros and negative zero do not create false evidence drift."""
        one = propose_postgresql_schema(
            "Equivalent Decimal",
            (ColumnEvidence("decimal_value", (Decimal("1.2300"), Decimal("-0"))),),
        )
        two = propose_postgresql_schema(
            "Equivalent Decimal",
            (ColumnEvidence("decimal_value", (Decimal("1.23"), Decimal("0"))),),
        )
        self.assertEqual(
            one.columns[0].evidence_fingerprint_sha256,
            two.columns[0].evidence_fingerprint_sha256,
        )
        self.assertEqual(
            one.proposal_fingerprint_sha256,
            two.proposal_fingerprint_sha256,
        )


if __name__ == "__main__":
    unittest.main()
