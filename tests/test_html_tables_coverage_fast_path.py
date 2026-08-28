from mhtml_etl_gateway.html_tables import _normalize_text


def test_normalize_empty_list():
    assert _normalize_text([]) == ""


def test_normalize_single_whitespace_only():
    assert _normalize_text(["   \n\t  "]) == ""
