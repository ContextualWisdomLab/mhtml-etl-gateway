"""Synthetic realistic SAP-style export regression tests."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.html_tables import extract_tables
from mhtml_etl_gateway.inspection import inspect_mhtml_bytes
from mhtml_etl_gateway.mime_parser import parse_mhtml_bytes
from tests.fixture_factory import make_mhtml


class RealisticExportTests(unittest.TestCase):
    """Verify a business-shaped table rather than toy single-cell input."""

    def test_sap_style_export_keeps_codes_dates_korean_and_rich_text(self) -> None:
        """Extraction preserves source truth while public inspection stays value-free."""
        headers = ("MANDT", "GUID", "DOCNOSUB", "TITLE", "DUEDT", "KUNNR")
        first_guid = "018f0c44-7b2a-7cc0-98c4-dc0c0c07398f"
        second_guid = "018f0c44-7b2b-7b51-a06f-7c84d44e6d29"
        first_document = "018f0c44-7b2c-795d-84bc-3d4878156c72"
        second_document = "018f0c44-7b2d-7e08-8ea7-f6cc878f6088"
        html = f"""
        <html><body><table>
          <tr>{''.join(f'<td>{header}</td>' for header in headers)}</tr>
          <tr><td>100</td><td>{first_guid}</td><td>{first_document}</td><td>고객 문의<br>후속 조치</td><td>20250131</td><td>0012345678</td></tr>
          <tr><td>100</td><td>{second_guid}</td><td>{second_document}</td><td>품질 점검<img src="data:image/png;base64,AAAA"></td><td>20250201</td><td>0098765432</td></tr>
        </table></body></html>
        """
        source = make_mhtml(html, content_transfer_encoding="text/html")

        extracted = extract_tables(parse_mhtml_bytes(source))[0]
        self.assertEqual(extracted.headers, headers)
        self.assertEqual(extracted.row_count, 3)
        self.assertEqual(extracted.data_row_count, 2)
        self.assertEqual(extracted.column_count, len(headers))
        self.assertEqual(extracted.rows[1][1].text, first_guid)
        self.assertEqual(extracted.rows[1][3].text, "고객 문의\n후속 조치")
        self.assertEqual(extracted.rows[1][5].text, "0012345678")

        report = inspect_mhtml_bytes(source)
        table = report.tables[0]
        self.assertEqual(table.header_value_count, len(headers))
        self.assertEqual(table.row_count, 3)
        self.assertEqual(table.data_row_count, 2)
        self.assertEqual(table.column_count, len(headers))
        rendered = repr(report.to_dict())
        self.assertNotIn("0012345678", rendered)
        self.assertNotIn("AAAA", rendered)
        self.assertNotIn("고객 문의", rendered)
        self.assertNotIn(first_guid, rendered)


if __name__ == "__main__":
    unittest.main()
