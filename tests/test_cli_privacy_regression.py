"""Regression tests for value-free public CLI load summaries."""

from __future__ import annotations

import json

from mhtml_etl_gateway import cli


def test_safe_load_summary_never_reflects_decoded_header_values() -> None:
    """Public load summaries expose a count, never source-controlled header text."""

    summary = cli._safe_load_summary(
        {
            "headers": [
                "<script>header()</script>",
                "<script>xheader()</script>",
            ]
        }
    )

    assert summary["header_count"] == 2
    assert "headers" not in summary
    serialized = json.dumps(summary)
    assert "script" not in serialized
    assert "header()" not in serialized
