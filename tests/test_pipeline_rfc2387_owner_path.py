"""Owner-path regressions for RFC 2387 root selection."""

from __future__ import annotations

from email.message import EmailMessage
from email.policy import default

import pytest

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.extraction_receipt import extract_table_with_receipt


def _related_message(
    first: EmailMessage,
    second: EmailMessage,
    *,
    start: str | None,
) -> bytes:
    """Build a two-part multipart/related message in deterministic body order."""
    root = EmailMessage(policy=default)
    root.set_type("multipart/related")
    root.set_param("type", "text/html")
    if start is not None:
        root.set_param("start", f"<{start}>")
    root.attach(first)
    root.attach(second)
    return root.as_bytes(policy=default)


def _html_part(html: str, content_id: str) -> EmailMessage:
    """Build one UTF-8 HTML body part with an explicit Content-ID."""
    part = EmailMessage(policy=default)
    part.set_content(html, subtype="html", charset="utf-8")
    part["Content-ID"] = f"<{content_id}>"
    return part


def test_receipt_path_honors_explicit_start_over_larger_later_html() -> None:
    """A larger non-root HTML part cannot replace the RFC 2387 start target."""
    authoritative = _html_part(
        "<html><body><table><tr><th>root_header</th></tr>"
        "<tr><td>root_value</td></tr></table></body></html>",
        "root-part",
    )
    decoy = _html_part(
        "<html><body><table><tr><th>decoy_header</th></tr>"
        + "".join(f"<tr><td>decoy_{index}</td></tr>" for index in range(32))
        + "</table></body></html>",
        "later-part",
    )
    source = _related_message(authoritative, decoy, start="root-part")

    bound = extract_table_with_receipt("ignored.mhtml", data=source)

    assert bound.headers == ("root_header",)
    assert bound.rows == (("root_value",),)
    assert bound.receipt.selected_component == "mime-part:0.table:0"


def test_receipt_path_rejects_non_html_first_direct_root_without_start() -> None:
    """Without start, a non-HTML first direct body part fails closed."""
    first = EmailMessage(policy=default)
    first.set_content("authoritative non-html body", subtype="plain", charset="utf-8")
    first["Content-ID"] = "<plain-root>"
    later_html = _html_part(
        "<html><body><table><tr><th>later_header</th></tr>"
        "<tr><td>later_value</td></tr></table></body></html>",
        "later-html",
    )
    source = _related_message(first, later_html, start=None)

    with pytest.raises(MhtmlGatewayError) as caught:
        extract_table_with_receipt("ignored.mhtml", data=source)

    assert caught.value.code == ErrorCode.MISSING_HTML_ROOT
