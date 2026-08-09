"""Command-line interface for safe MHTML structure inspection."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import NoReturn

from .errors import ErrorCode, MhtmlGatewayError
from .inspection import inspect_mhtml_file
from .models import ParseLimits


class _ArgumentParserError(Exception):
    """Internal signal used to route argparse failures through JSON output."""


class _JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that never writes source-derived usage failures itself."""

    def error(self, message: str) -> NoReturn:
        """Raise an internal signal instead of printing conventional usage text."""
        del message
        raise _ArgumentParserError


def _build_parser() -> argparse.ArgumentParser:
    """Create the public command-line argument parser."""
    parser = _JsonArgumentParser(prog="mhtml-etl-gateway")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="emit metadata-only structure for an MHTML source",
    )
    inspect_parser.add_argument("source_path")
    inspect_parser.add_argument("--pretty", action="store_true")
    inspect_parser.add_argument(
        "--max-source-bytes",
        type=int,
        default=ParseLimits().max_source_bytes,
    )
    return parser


def _write_error(error: MhtmlGatewayError) -> int:
    """Write one fixed JSON error object and return the conventional status."""
    print(
        json.dumps(error.to_dict(), ensure_ascii=False, sort_keys=True),
        file=sys.stderr,
    )
    return 2


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the CLI and return a conventional process status code."""
    parser = _build_parser()
    try:
        namespace = parser.parse_args(arguments)
    except _ArgumentParserError:
        return _write_error(MhtmlGatewayError(ErrorCode.INVALID_ARGUMENT))

    try:
        limits = ParseLimits(max_source_bytes=namespace.max_source_bytes)
    except ValueError:
        return _write_error(MhtmlGatewayError(ErrorCode.INVALID_ARGUMENT))

    try:
        report = inspect_mhtml_file(namespace.source_path, limits=limits)
    except MhtmlGatewayError as error:
        return _write_error(error)

    indent = 2 if namespace.pretty else None
    print(
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=indent,
            separators=None if namespace.pretty else (",", ":"),
        )
    )
    return 0
