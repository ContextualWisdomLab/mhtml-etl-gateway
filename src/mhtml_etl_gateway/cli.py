"""Command-line interface for safe MHTML structure inspection."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .errors import MhtmlGatewayError
from .inspection import inspect_mhtml_file
from .models import ParseLimits


def _build_parser() -> argparse.ArgumentParser:
    """Create the public command-line argument parser."""
    parser = argparse.ArgumentParser(prog="mhtml-etl-gateway")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="emit metadata-only structure for an MHTML source",
    )
    inspect_parser.add_argument("source_path")
    inspect_parser.add_argument("--pretty", action="store_true")
    inspect_parser.add_argument(
        "--include-header-values",
        action="store_true",
        help="include cell-derived header values in the local output",
    )
    inspect_parser.add_argument(
        "--max-source-bytes",
        type=int,
        default=ParseLimits().max_source_bytes,
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the CLI and return a conventional process status code."""
    parser = _build_parser()
    namespace = parser.parse_args(arguments)
    try:
        limits = ParseLimits(max_source_bytes=namespace.max_source_bytes)
        report = inspect_mhtml_file(
            namespace.source_path,
            limits=limits,
            include_header_values=namespace.include_header_values,
        )
    except (MhtmlGatewayError, ValueError) as error:
        payload = (
            error.to_dict()
            if isinstance(error, MhtmlGatewayError)
            else {"error_code": "invalid_argument", "message": str(error)}
        )
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2

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
