"""Immutability tests for schema proposal policy vocabularies."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.schema_proposal import (
    SchemaProposalError,
    SchemaProposalErrorCode,
    SchemaProposalPolicy,
)


class SchemaProposalPolicyImmutabilityTests(unittest.TestCase):
    """Reject mutable policy collections inside an otherwise frozen dataclass."""

    def test_boolean_and_date_vocabularies_must_be_tuples(self) -> None:
        """Lists cannot mutate policy identity after proposal construction."""
        invalid = (
            {"boolean_true_values": ["true"]},
            {"boolean_false_values": ["false"]},
            {"date_formats": ["%Y%m%d"]},
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(
                SchemaProposalError
            ) as caught:
                SchemaProposalPolicy(**arguments)  # type: ignore[arg-type]
            self.assertEqual(
                caught.exception.code,
                SchemaProposalErrorCode.INVALID_POLICY,
            )


if __name__ == "__main__":
    unittest.main()
