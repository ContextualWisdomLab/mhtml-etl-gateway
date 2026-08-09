"""Security and resource-limit tests for value-free schema proposals."""

from __future__ import annotations

from decimal import Decimal
import json
import math
import unittest

from mhtml_etl_gateway.schema_proposal import (
    ColumnEvidence,
    SchemaProposalError,
    SchemaProposalErrorCode,
    SchemaProposalPolicy,
    propose_postgresql_schema,
)


class SchemaProposalSecurityTests(unittest.TestCase):
    """Verify fixed errors and fail-closed policy/input boundaries."""

    def test_public_error_messages_never_reflect_protected_values(self) -> None:
        """Input failures expose only fixed approved-safe messages."""
        cases = (
            lambda: ColumnEvidence(123, ()),  # type: ignore[arg-type]
            lambda: ColumnEvidence("secret", ["ultra-private"]),  # type: ignore[arg-type]
            lambda: propose_postgresql_schema("", (ColumnEvidence("x", (1,)),)),
            lambda: propose_postgresql_schema("table", ()),
            lambda: propose_postgresql_schema(
                "table",
                (ColumnEvidence("x", (object(),)),),
            ),
        )
        for call in cases:
            with self.subTest(call=call), self.assertRaises(SchemaProposalError) as caught:
                call()
            rendered = json.dumps(caught.exception.to_dict())
            self.assertNotIn("secret", rendered)
            self.assertNotIn("ultra-private", rendered)

    def test_policy_limits_and_vocabularies_fail_closed(self) -> None:
        """Invalid versions, limits, vocabularies, and date formats are rejected."""
        invalid_policies = (
            {"policy_version": ""},
            {"max_columns": 0},
            {"max_samples_per_column": True},
            {"max_identifier_bytes": 15},
            {"boolean_true_values": ("yes",), "boolean_false_values": ("YES",)},
            {"boolean_true_values": ()},
            {"boolean_true_values": ("",)},
            {"boolean_true_values": (1,)},
            {"date_formats": ()},
            {"date_formats": ("",)},
        )
        for arguments in invalid_policies:
            with self.subTest(arguments=arguments), self.assertRaises(SchemaProposalError) as caught:
                SchemaProposalPolicy(**arguments)
            self.assertEqual(caught.exception.code, SchemaProposalErrorCode.INVALID_POLICY)

    def test_column_sample_and_value_limits_fail_closed(self) -> None:
        """Column counts, samples, labels, and canonical values remain bounded."""
        with self.assertRaises(SchemaProposalError) as caught:
            propose_postgresql_schema(
                "table",
                (ColumnEvidence("a", ()), ColumnEvidence("b", ())),
                policy=SchemaProposalPolicy(max_columns=1),
            )
        self.assertEqual(caught.exception.code, SchemaProposalErrorCode.TOO_MANY_COLUMNS)

        with self.assertRaises(SchemaProposalError) as caught:
            propose_postgresql_schema(
                "table",
                (ColumnEvidence("a", (1, 2)),),
                policy=SchemaProposalPolicy(max_samples_per_column=1),
            )
        self.assertEqual(caught.exception.code, SchemaProposalErrorCode.TOO_MANY_SAMPLES)

        for oversized in (
            "x" * 5,
            10**100,
            10_000,
            Decimal("1" * 100),
            Decimal("1E+100"),
        ):
            with self.subTest(kind=type(oversized).__name__), self.assertRaises(SchemaProposalError) as caught:
                propose_postgresql_schema(
                    "table",
                    (ColumnEvidence("a", (oversized,)),),
                    policy=SchemaProposalPolicy(max_value_characters=4),
                )
            self.assertEqual(caught.exception.code, SchemaProposalErrorCode.VALUE_TOO_LARGE)

        for unsupported in (b"secret", math.inf, Decimal("NaN")):
            with self.subTest(kind=type(unsupported).__name__), self.assertRaises(SchemaProposalError) as caught:
                propose_postgresql_schema(
                    "table",
                    (ColumnEvidence("a", (unsupported,)),),
                )
            self.assertEqual(caught.exception.code, SchemaProposalErrorCode.UNSUPPORTED_VALUE)

    def test_invalid_sequence_headers_and_labels_fail_closed(self) -> None:
        """Mutable lists, foreign objects, blank headers, and long labels are rejected."""
        cases = (
            lambda: propose_postgresql_schema("table", "not-columns"),  # type: ignore[arg-type]
            lambda: propose_postgresql_schema(
                "table",
                [ColumnEvidence("x", (1,))],
            ),  # type: ignore[arg-type]
            lambda: propose_postgresql_schema("table", (object(),)),  # type: ignore[arg-type]
            lambda: propose_postgresql_schema("table", (ColumnEvidence(" ", (1,)),)),
            lambda: propose_postgresql_schema(
                "x" * 5,
                (ColumnEvidence("a", (1,)),),
                policy=SchemaProposalPolicy(max_header_characters=4),
            ),
            lambda: propose_postgresql_schema(
                "t",
                (ColumnEvidence("x" * 5, (1,)),),
                policy=SchemaProposalPolicy(max_header_characters=4),
            ),
        )
        for call in cases:
            with self.subTest(call=call), self.assertRaises(SchemaProposalError):
                call()


if __name__ == "__main__":
    unittest.main()
