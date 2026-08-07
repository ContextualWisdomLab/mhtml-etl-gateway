"""Synthetic realistic SAP-style export regression tests."""

from __future__ import annotations

import unittest

from mhtml_etl_gateway.inspection import inspect_mhtml_bytes
from tests.fixture_factory import make_mhtml


class RealisticExportTests(unittest.TestCase):
    """Verify a business-shaped table rather than toy single-cell input."""

    def test_sap_style_export_keeps_codes_dates_korean_and_rich_text(self) -> None:
        """Inspection preserves structural truth for a representative export."""
        headers = ("MANDT", "GUID", "DOCNOSUB", "TITLE", "DUEDT", "KUNNR")
        html = """
        <html><body><table>
          <tr>{headers}</tr>
          <tr><td>100</td><td>018f</td><td>0001</td><td>고객 문의<br>후속 조치</td><td>20250131</td><td>0012345678</td></tr>
          <tr><td>100</td><td>0190</td><td>0002</td><td>품질 점검<img src="data:image/png;base64,AAAA"></td><td>20250201</td><td>0098765432</td></tr>
        </table></body></html>
        """.format(headers="".join(f"<td>{header}</td>" for header in headers))
        source = make_mhtml(html, content_transfer_encoding="text/html")
        default_table = inspect_mhtml_bytes(source).tables[0]
        self.assertEqual(default_table.headers, ())
        report = inspect_mhtml_bytes(source, include_header_values=True)
        table = report.tables[0]
        self.assertEqual(table.headers, headers)
        self.assertEqual(table.row_count, 3)
        self.assertEqual(table.data_row_count, 2)
        self.assertEqual(table.column_count, len(headers))
        self.assertNotIn("0012345678", repr(report.to_dict()))
        self.assertNotIn("AAAA", repr(report.to_dict()))


if __name__ == "__main__":
    unittest.main()
