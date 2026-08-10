from __future__ import annotations

import pytest

from mhtml_etl_gateway.mhtml_parser import (
    MhtmlParseError,
    extract_html_bytes,
    parse_mhtml_parts,
)


def test_parse_fixture_parts(sample_mhtml_bytes: bytes) -> None:
    parts = parse_mhtml_parts(sample_mhtml_bytes)
    assert parts
    assert any(p.content_type == "text/html" for p in parts)
    html = extract_html_bytes(sample_mhtml_bytes)
    assert b"<table" in html.lower()
    assert b"MANDT" in html
    assert b"GUID" in html


def test_empty_input_fails_closed() -> None:
    with pytest.raises(MhtmlParseError):
        parse_mhtml_parts(b"")
    with pytest.raises(MhtmlParseError):
        parse_mhtml_parts(b"   \n")


def test_non_mhtml_garbage_fails_closed() -> None:
    with pytest.raises(MhtmlParseError):
        parse_mhtml_parts(b"not-a-mime-document-at-all")
