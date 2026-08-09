"""Tests for deterministic, value-free PostgreSQL schema proposals."""

from __future__ import annotations

import re
from pathlib import Path
import unittest

from mhtml_etl_gateway.schema_proposal import (
    PostgresType,
    ProtectedColumnInput,
    SchemaProposalError,
    SchemaProposalErrorCode,
    SchemaProposalPolicy,
    propose_schema,
)


_SOURCE_HASH = "a" * 64
_ROOT = Path(__file__).resolve().parents[1]


class SchemaProposalTests(unittest.TestCase):
    """Verify conservative inference, naming, identity, and nonreflection."""

    def test_sap_shaped_columns_receive_governed_names_and_types(self) -> None:
        """SAP identifiers remain text while date, boolean, and decimal evidence types safely."""
        proposal = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput("MANDT", ("100", "200"), complete=True),
                ProtectedColumnInput(
                    "GUID",
                    (
                        "01912345-6789-7abc-8def-0123456789ab",
                        "01912345-6789-7abc-8def-0123456789ac",
                    ),
                    complete=True,
                ),
                ProtectedColumnInput("DOCNOSUB", ("0001", "0002"), complete=True),
                ProtectedColumnInput("DUEDT", ("20250131", "20250201"), complete=True),
                ProtectedColumnInput("KUNNR", ("0012345678", None), complete=True),
                ProtectedColumnInput("승인 여부", ("TRUE", "false"), complete=True),
                ProtectedColumnInput("amountTotal", ("12.50", "0.00"), complete=True),
            ),
        )
        columns = proposal.columns
        self.assertEqual(
            [column.target_column_name for column in columns],
            [
                "client_code",
                "global_identifier",
                "document_subnumber",
                "due_date",
                "customer_number",
                "승인_여부",
                "amount_total",
            ],
        )
        self.assertEqual(
            [column.proposed_type for column in columns],
            [
                PostgresType.TEXT,
                PostgresType.TEXT,
                PostgresType.TEXT,
                PostgresType.DATE,
                PostgresType.TEXT,
                PostgresType.BOOLEAN,
                PostgresType.NUMERIC,
            ],
        )
        self.assertIn("identifier_semantics", columns[0].review_reasons)
        self.assertIn("identifier_semantics", columns[1].review_reasons)
        self.assertIn("leading_zero_identifier", columns[2].review_reasons)
        self.assertFalse(columns[3].nullable)
        self.assertTrue(columns[4].nullable)
        self.assertEqual(columns[4].non_null_count, 1)
        self.assertEqual(columns[4].distinct_count, 1)
        self.assertEqual(columns[5].review_reasons, ())
        self.assertEqual(columns[6].maximum_numeric_scale, 2)

    def test_sample_only_nullability_remains_conservative(self) -> None:
        """A sample without nulls cannot manufacture a NOT NULL proposal."""
        sampled = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("orderCount", ("1", "2")),),
        ).columns[0]
        complete = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("orderCount", ("1", "2"), complete=True),),
        ).columns[0]
        self.assertTrue(sampled.nullable)
        self.assertIn("sample_only_nullability", sampled.review_reasons)
        self.assertFalse(complete.nullable)
        self.assertNotIn("sample_only_nullability", complete.review_reasons)
        self.assertEqual(complete.proposed_type, PostgresType.BIGINT)

    def test_null_and_empty_columns_remain_nullable_text(self) -> None:
        """Blank-only evidence does not invent a concrete PostgreSQL type."""
        proposal = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput("emptyValue", (None, "", "   "), complete=True),
            ),
        ).columns[0]
        self.assertEqual(proposal.proposed_type, PostgresType.TEXT)
        self.assertTrue(proposal.nullable)
        self.assertEqual(proposal.non_null_count, 0)
        self.assertEqual(proposal.distinct_count, 0)
        self.assertIn("empty_column", proposal.review_reasons)

    def test_dates_require_both_valid_values_and_header_semantics(self) -> None:
        """Date-shaped identifiers remain text when the header supplies no date meaning."""
        date_column = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("createdDate", ("2025-01-31",), complete=True),),
        ).columns[0]
        ambiguous = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("batchCode", ("20250131",), complete=True),),
        ).columns[0]
        invalid = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("createdDate", ("2025-02-30",), complete=True),),
        ).columns[0]
        self.assertEqual(date_column.proposed_type, PostgresType.DATE)
        self.assertEqual(ambiguous.proposed_type, PostgresType.TEXT)
        self.assertIn("date_semantics_missing", ambiguous.review_reasons)
        self.assertEqual(invalid.proposed_type, PostgresType.TEXT)
        self.assertIn("mixed_or_unrecognized_values", invalid.review_reasons)

    def test_leading_zero_and_identifier_headers_override_numeric_shapes(self) -> None:
        """Lossless identifiers are never converted into numeric PostgreSQL values."""
        proposal = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput("accountNumber", ("123", "456"), complete=True),
                ProtectedColumnInput("batchValue", ("001", "002"), complete=True),
                ProtectedColumnInput("signedValue", ("-001", "+002"), complete=True),
            ),
        )
        for column in proposal.columns:
            self.assertEqual(column.proposed_type, PostgresType.TEXT)
        self.assertIn("identifier_semantics", proposal.columns[0].review_reasons)
        self.assertIn("leading_zero_identifier", proposal.columns[1].review_reasons)
        self.assertIn("leading_zero_identifier", proposal.columns[2].review_reasons)

    def test_bigint_overflow_uses_numeric_with_review_evidence(self) -> None:
        """An integral value outside signed bigint remains lossless as numeric."""
        within = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("itemCount", (str(2**63 - 1),), complete=True),),
        ).columns[0]
        overflow = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("itemCount", (str(2**63),), complete=True),),
        ).columns[0]
        self.assertEqual(within.proposed_type, PostgresType.BIGINT)
        self.assertEqual(overflow.proposed_type, PostgresType.NUMERIC)
        self.assertIn("bigint_range_exceeded", overflow.review_reasons)
        self.assertEqual(overflow.maximum_numeric_scale, 0)

    def test_boolean_vocabulary_is_exact_and_conservative(self) -> None:
        """Only true and false are automatic boolean evidence."""
        boolean = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("activeFlag", ("true", "FALSE"), complete=True),),
        ).columns[0]
        not_boolean = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("activeFlag", ("yes", "no"), complete=True),),
        ).columns[0]
        self.assertEqual(boolean.proposed_type, PostgresType.BOOLEAN)
        self.assertEqual(not_boolean.proposed_type, PostgresType.TEXT)
        self.assertIn("mixed_or_unrecognized_values", not_boolean.review_reasons)

    def test_mixed_values_fall_back_to_text(self) -> None:
        """Mixed numeric and textual evidence is never partially coerced."""
        column = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("metricValue", ("1.2", "unknown"), complete=True),),
        ).columns[0]
        self.assertEqual(column.proposed_type, PostgresType.TEXT)
        self.assertIn("mixed_or_unrecognized_values", column.review_reasons)

    def test_unicode_and_camel_case_names_normalize_deterministically(self) -> None:
        """Compatibility characters normalize without changing exact source fingerprints."""
        ascii_proposal = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("Customer Number", ("1",)),),
        ).columns[0]
        full_width = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("Ｃｕｓｔｏｍｅｒ　Ｎｕｍｂｅｒ", ("1",)),),
        ).columns[0]
        acronym = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput("HTTPResponseCode", ("200",)),),
        ).columns[0]
        self.assertEqual(ascii_proposal.target_column_name, "customer_number")
        self.assertEqual(full_width.target_column_name, "customer_number")
        self.assertNotEqual(
            ascii_proposal.source_header_hash_sha256,
            full_width.source_header_hash_sha256,
        )
        self.assertEqual(acronym.target_column_name, "http_response_code")

    def test_single_word_reserved_numeric_and_empty_names_are_safe(self) -> None:
        """Every generated identifier has multiple words and a legal starting character."""
        proposal = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput("select", ("x",)),
                ProtectedColumnInput("123", ("x",)),
                ProtectedColumnInput("", ("x",)),
                ProtectedColumnInput("😀", ("x",)),
            ),
        )
        names = [column.target_column_name for column in proposal.columns]
        self.assertEqual(names[0], "select_field")
        self.assertEqual(names[1], "source_123")
        self.assertRegex(names[2], r"^source_field_[0-9a-f]{8}$")
        self.assertRegex(names[3], r"^source_field_[0-9a-f]{8}$")
        for name in names:
            self.assertGreaterEqual(len(name.split("_")), 2)
            self.assertLessEqual(len(name.encode("utf-8")), 63)

    def test_long_utf8_identifier_is_truncated_on_a_character_boundary(self) -> None:
        """PostgreSQL's 63-byte identifier limit is respected without invalid UTF-8."""
        header = "고객" * 40 + " 번호"
        column = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput(header, ("x",)),),
        ).columns[0]
        encoded = column.target_column_name.encode("utf-8")
        self.assertLessEqual(len(encoded), 63)
        self.assertEqual(encoded.decode("utf-8"), column.target_column_name)
        self.assertGreaterEqual(len(column.target_column_name.split("_")), 2)

    def test_collisions_receive_deterministic_opaque_suffixes(self) -> None:
        """Equivalent names remain unique without sequential public identifiers."""
        columns = (
            ProtectedColumnInput("Customer Number", ("1",)),
            ProtectedColumnInput("customer-number", ("2",)),
            ProtectedColumnInput("Customer Number", ("3",)),
        )
        first = propose_schema(_SOURCE_HASH, columns)
        second = propose_schema(_SOURCE_HASH, columns)
        names = [column.target_column_name for column in first.columns]
        self.assertEqual(first, second)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[0], "customer_number")
        self.assertRegex(names[1], r"^customer_number_[0-9a-f]{8}$")
        self.assertRegex(names[2], r"^customer_number_[0-9a-f]{8}$")
        self.assertNotRegex(names[1], r"_[0-9]+$")

    def test_identity_is_deterministic_and_order_sensitive(self) -> None:
        """Identical protected inputs reproduce; reordering changes proposal identity."""
        columns = (
            ProtectedColumnInput("firstValue", ("1",)),
            ProtectedColumnInput("secondValue", ("2",)),
        )
        first = propose_schema(_SOURCE_HASH.upper(), columns)
        repeated = propose_schema(_SOURCE_HASH, columns)
        reversed_proposal = propose_schema(_SOURCE_HASH, tuple(reversed(columns)))
        self.assertEqual(first, repeated)
        self.assertEqual(first.source_hash_sha256, _SOURCE_HASH)
        self.assertRegex(first.schema_proposal_id, r"^schema_proposal_[0-9a-f]{32}$")
        self.assertNotEqual(
            first.schema_proposal_id,
            reversed_proposal.schema_proposal_id,
        )
        self.assertNotEqual(
            first.table_fingerprint_sha256,
            reversed_proposal.table_fingerprint_sha256,
        )
        self.assertEqual(
            [column.target_column_name for column in reversed_proposal.columns],
            ["second_value", "first_value"],
        )

    def test_serialization_contains_no_raw_headers_or_sample_values(self) -> None:
        """The proposal artifact contains hashes, derived names, and aggregate evidence only."""
        raw_header = "Internal Customer Secret"
        raw_value = "customer-value-that-must-not-leak"
        proposal = propose_schema(
            _SOURCE_HASH,
            (ProtectedColumnInput(raw_header, (raw_value, None)),),
        )
        rendered = repr(proposal.to_dict())
        self.assertNotIn(raw_header, rendered)
        self.assertNotIn(raw_value, rendered)
        self.assertNotIn("values", proposal.to_dict()["columns"][0])
        self.assertEqual(proposal.to_dict()["proposal_version"], "1.0.0")

    def test_numeric_aggregate_evidence_is_bounded_and_value_free(self) -> None:
        """Precision, scale, and text length summarize values without serializing them."""
        column = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput(
                    "averageScore",
                    ("-12.340", "0.1", None),
                    complete=True,
                ),
            ),
        ).columns[0]
        self.assertEqual(column.proposed_type, PostgresType.NUMERIC)
        self.assertEqual(column.maximum_numeric_precision, 5)
        self.assertEqual(column.maximum_numeric_scale, 3)
        self.assertEqual(column.maximum_text_length, 7)
        self.assertTrue(column.nullable)

    def test_policy_version_changes_proposal_identity(self) -> None:
        """Algorithm policy is part of the content-addressed proposal identity."""
        column = (ProtectedColumnInput("metricValue", ("1",)),)
        first = propose_schema(
            _SOURCE_HASH,
            column,
            policy=SchemaProposalPolicy(algorithm_version="1.0.0"),
        )
        second = propose_schema(
            _SOURCE_HASH,
            column,
            policy=SchemaProposalPolicy(algorithm_version="1.0.1"),
        )
        self.assertNotEqual(first.schema_proposal_id, second.schema_proposal_id)
        self.assertEqual(second.proposal_version, "1.0.1")

    def test_invalid_inputs_fail_with_fixed_nonreflecting_errors(self) -> None:
        """Input validation never reflects protected headers or values."""
        cases = (
            (
                SchemaProposalErrorCode.INVALID_SOURCE_HASH,
                lambda: propose_schema("not-a-hash", (ProtectedColumnInput("A", ("1",)),)),
            ),
            (
                SchemaProposalErrorCode.INVALID_INPUT,
                lambda: propose_schema(_SOURCE_HASH, ()),
            ),
            (
                SchemaProposalErrorCode.TOO_MANY_COLUMNS,
                lambda: propose_schema(
                    _SOURCE_HASH,
                    (
                        ProtectedColumnInput("A", ("1",)),
                        ProtectedColumnInput("B", ("2",)),
                    ),
                    policy=SchemaProposalPolicy(max_columns=1),
                ),
            ),
            (
                SchemaProposalErrorCode.HEADER_TOO_LARGE,
                lambda: propose_schema(
                    _SOURCE_HASH,
                    (ProtectedColumnInput("secret-header", ("1",)),),
                    policy=SchemaProposalPolicy(max_header_chars=3),
                ),
            ),
            (
                SchemaProposalErrorCode.TOO_MANY_SAMPLES,
                lambda: propose_schema(
                    _SOURCE_HASH,
                    (ProtectedColumnInput("A", ("1", "2")),),
                    policy=SchemaProposalPolicy(max_samples_per_column=1),
                ),
            ),
            (
                SchemaProposalErrorCode.SAMPLE_VALUE_TOO_LARGE,
                lambda: propose_schema(
                    _SOURCE_HASH,
                    (ProtectedColumnInput("A", ("secret-value",)),),
                    policy=SchemaProposalPolicy(max_value_chars=3),
                ),
            ),
            (
                SchemaProposalErrorCode.INVALID_INPUT,
                lambda: propose_schema(
                    _SOURCE_HASH,
                    (ProtectedColumnInput("A", (1,)),),  # type: ignore[arg-type]
                ),
            ),
        )
        for expected_code, operation in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(SchemaProposalError) as caught:
                    operation()
                self.assertEqual(caught.exception.code, expected_code)
                self.assertNotIn("secret", caught.exception.message)
                self.assertEqual(
                    caught.exception.to_dict(),
                    {
                        "error_code": expected_code.value,
                        "message": caught.exception.message,
                    },
                )

    def test_policy_rejects_invalid_budgets_and_versions(self) -> None:
        """Every policy budget and version identifier is explicit and valid."""
        for keyword in (
            "max_columns",
            "max_header_chars",
            "max_samples_per_column",
            "max_value_chars",
        ):
            with self.subTest(keyword=keyword), self.assertRaises(ValueError):
                SchemaProposalPolicy(**{keyword: 0})
            with self.subTest(keyword=keyword + "_bool"), self.assertRaises(ValueError):
                SchemaProposalPolicy(**{keyword: True})
        with self.assertRaises(ValueError):
            SchemaProposalPolicy(algorithm_version="")
        with self.assertRaises(ValueError):
            SchemaProposalPolicy(algorithm_version=1)  # type: ignore[arg-type]

    def test_protected_column_input_rejects_invalid_container_types(self) -> None:
        """Headers, value tuples, and completeness flags have exact runtime contracts."""
        with self.assertRaises(ValueError):
            ProtectedColumnInput(1, ())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            ProtectedColumnInput("A", ["1"])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            ProtectedColumnInput("A", (), complete=1)  # type: ignore[arg-type]

    def test_production_module_has_no_ddl_network_or_database_escape(self) -> None:
        """The proposal layer remains a pure in-process decision artifact."""
        source = (
            _ROOT / "src/mhtml_etl_gateway/schema_proposal.py"
        ).read_text(encoding="utf-8").lower()
        forbidden = (
            "create table",
            "alter table",
            "psycopg",
            "sqlalchemy",
            "subprocess",
            "socket",
            "requests",
            "urllib.request",
        )
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_all_target_names_match_multiword_snake_case_contract(self) -> None:
        """Generated names remain lowercase, unique, and underscore-separated."""
        proposal = propose_schema(
            _SOURCE_HASH,
            (
                ProtectedColumnInput("simple", ("x",)),
                ProtectedColumnInput("two words", ("x",)),
                ProtectedColumnInput("한국어 이름", ("x",)),
            ),
        )
        pattern = re.compile(r"^[^_\W][\w]*_[\w]+(?:_[\w]+)*$", re.UNICODE)
        names = [column.target_column_name for column in proposal.columns]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertEqual(name, name.lower())
            self.assertRegex(name, pattern)


if __name__ == "__main__":
    unittest.main()
