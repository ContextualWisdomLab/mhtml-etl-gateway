"""Synthetic MHTML fixture builders used by the test suite."""

from __future__ import annotations

from email.message import EmailMessage
from email.policy import default


def make_mhtml(
    html: str,
    *,
    html_content_id: str = "root-part",
    start: str | None = "root-part",
    charset: str = "utf-8",
    include_decoy: bool = False,
    content_transfer_encoding: str | None = None,
    content_location: str | None = "file:///root.html",
) -> bytes:
    """Return a small RFC 2387-style MHTML message for tests."""
    root = EmailMessage(policy=default)
    root.set_type("multipart/related")
    root.set_param("type", "text/html")
    if start is not None:
        root.set_param("start", f"<{start}>")

    if include_decoy:
        decoy = EmailMessage(policy=default)
        decoy.set_content("<html><table><tr><td>DECOY</td></tr></table></html>", subtype="html", charset="utf-8")
        decoy["Content-ID"] = "<decoy-part>"
        decoy["Content-Location"] = "file:///decoy.html"
        root.attach(decoy)

    html_part = EmailMessage(policy=default)
    html_part.set_content(
        html,
        subtype="html",
        charset=charset,
        cte="8bit" if content_transfer_encoding is not None else None,
    )
    html_part["Content-ID"] = f"<{html_content_id}>"
    if content_location is not None:
        html_part["Content-Location"] = content_location
    if content_transfer_encoding is not None:
        del html_part["Content-Transfer-Encoding"]
        html_part["Content-Transfer-Encoding"] = content_transfer_encoding
    root.attach(html_part)
    return root.as_bytes(policy=default)


def make_standalone_html(html: str, *, charset: str = "utf-8") -> bytes:
    """Return a standalone text/html MIME message for tests."""
    message = EmailMessage(policy=default)
    message.set_content(html, subtype="html", charset=charset)
    message["Content-Location"] = "file:///standalone.html"
    return message.as_bytes(policy=default)
