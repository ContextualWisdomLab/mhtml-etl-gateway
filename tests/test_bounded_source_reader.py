"""Tests for bounded file reads before MHTML parsing and inspection."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mhtml_etl_gateway.errors import ErrorCode, MhtmlGatewayError
from mhtml_etl_gateway.inspection import inspect_mhtml_file
from mhtml_etl_gateway.mime_parser import parse_mhtml_file
from mhtml_etl_gateway.models import ParseLimits
from mhtml_etl_gateway.source_reader import (
    _READ_CHUNK_BYTES,
    _read_bounded_source,
)
from tests.fixture_factory import make_mhtml


class _RecordingStream(BytesIO):
    """Byte stream that records every bounded read request."""

    def __init__(self, content: bytes, read_sizes: list[int]) -> None:
        """Initialize the stream and shared read-size receipt."""
        super().__init__(content)
        self._read_sizes = read_sizes

    def read(self, size: int = -1) -> bytes:
        """Record the requested size before delegating to the byte stream."""
        self._read_sizes.append(size)
        return super().read(size)


class BoundedSourceReaderTests(unittest.TestCase):
    """Verify file entry points cannot allocate beyond the source budget first."""

    def test_reader_requests_only_one_byte_beyond_small_budget(self) -> None:
        """An oversized source is detected with a bounded six-byte read."""
        read_sizes: list[int] = []
        stream = _RecordingStream(b"0123456789", read_sizes)
        with patch(
            "mhtml_etl_gateway.source_reader.Path.open",
            return_value=stream,
        ):
            with self.assertRaises(MhtmlGatewayError) as caught:
                _read_bounded_source(
                    "ignored.mhtml",
                    limits=ParseLimits(max_source_bytes=5),
                )
        self.assertEqual(caught.exception.code, ErrorCode.SOURCE_TOO_LARGE)
        self.assertEqual(read_sizes, [6])

    def test_reader_chunks_without_one_unbounded_allocation(self) -> None:
        """A multi-megabyte exact-limit source is consumed in fixed-size chunks."""
        source = b"x" * (_READ_CHUNK_BYTES + 2)
        read_sizes: list[int] = []
        stream = _RecordingStream(source, read_sizes)
        with patch(
            "mhtml_etl_gateway.source_reader.Path.open",
            return_value=stream,
        ):
            result = _read_bounded_source(
                "ignored.mhtml",
                limits=ParseLimits(max_source_bytes=len(source)),
            )
        self.assertEqual(result, source)
        self.assertEqual(
            read_sizes,
            [_READ_CHUNK_BYTES, 3, 1],
        )
        self.assertLessEqual(max(read_sizes), _READ_CHUNK_BYTES)

    def test_empty_source_returns_without_overread(self) -> None:
        """An empty regular source performs one bounded read and returns empty bytes."""
        read_sizes: list[int] = []
        stream = _RecordingStream(b"", read_sizes)
        with patch(
            "mhtml_etl_gateway.source_reader.Path.open",
            return_value=stream,
        ):
            result = _read_bounded_source(
                "ignored.mhtml",
                limits=ParseLimits(max_source_bytes=4),
            )
        self.assertEqual(result, b"")
        self.assertEqual(read_sizes, [5])

    def test_reader_maps_file_errors_without_reflecting_path(self) -> None:
        """Open failures use the fixed source-read domain error."""
        source_path = "/private/customer/source.mhtml"
        with patch(
            "mhtml_etl_gateway.source_reader.Path.open",
            side_effect=OSError("private detail"),
        ):
            with self.assertRaises(MhtmlGatewayError) as caught:
                _read_bounded_source(source_path)
        self.assertEqual(caught.exception.code, ErrorCode.SOURCE_READ_FAILED)
        self.assertNotIn(source_path, caught.exception.message)
        self.assertNotIn("private detail", caught.exception.message)

    def test_default_limits_read_a_small_real_file(self) -> None:
        """The default-limit path reads a normal source without a mock stream."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.bin"
            path.write_bytes(b"small")
            self.assertEqual(_read_bounded_source(path), b"small")

    def test_parser_file_wrapper_enforces_limit_during_read(self) -> None:
        """The parser wrapper rejects oversize before MIME parsing."""
        source = make_mhtml("<table><tr><td>A</td></tr></table>")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(source)
            with self.assertRaises(MhtmlGatewayError) as caught:
                parse_mhtml_file(
                    path,
                    limits=ParseLimits(max_source_bytes=len(source) - 1),
                )
        self.assertEqual(caught.exception.code, ErrorCode.SOURCE_TOO_LARGE)

    def test_inspection_file_wrapper_uses_same_bounded_reader(self) -> None:
        """Inspection and parsing share one source-size enforcement boundary."""
        source = make_mhtml("<table><tr><td>A</td></tr></table>")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.mhtml"
            path.write_bytes(source)
            with self.assertRaises(MhtmlGatewayError) as caught:
                inspect_mhtml_file(
                    path,
                    limits=ParseLimits(max_source_bytes=len(source) - 1),
                )
        self.assertEqual(caught.exception.code, ErrorCode.SOURCE_TOO_LARGE)


if __name__ == "__main__":
    unittest.main()
