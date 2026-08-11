"""Command-line interface for safe MHTML inspection and PostgreSQL ETL."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from .batch import run_batch
from .errors import ErrorCode, MhtmlGatewayError
from .inspection import inspect_mhtml_file
from .models import ParseLimits
from .pipeline import convert_mhtml_to_postgres
from .postgres_loader import OnDuplicate


class _ArgumentParserError(Exception):
    """Internal signal used to route argparse failures through JSON output."""


class _JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that never reflects source-derived usage failures."""

    def error(self, message: str) -> NoReturn:
        """Raise an internal signal instead of printing conventional usage text."""
        del message
        raise _ArgumentParserError


def _parse_required_headers(value: str | None) -> list[str] | None:
    """Parse an optional comma-separated required-header contract."""
    if value is None:
        return None
    value = value.strip()
    if value == "" or value.lower() == "none":
        return []
    return [header.strip() for header in value.split(",") if header.strip()]


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add shared ETL options to load and batch subcommands."""
    parser.add_argument(
        "--dsn",
        default=os.environ.get("MHTML_ETL_DSN") or os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URI (or set MHTML_ETL_DSN / DATABASE_URL).",
    )
    parser.add_argument(
        "--table-name",
        default=None,
        help="Override target table name (multiword snake_case applied).",
    )
    parser.add_argument(
        "--column-mapping",
        "--column-comments",
        dest="column_mapping",
        default=None,
        help="Column mapping reference (.json, .csv, or .pptx) for COMMENT ON COLUMN.",
    )
    parser.add_argument(
        "--on-duplicate",
        choices=("skip", "replace"),
        default="skip",
        help="Idempotency: skip an already loaded artifact or replace its rows.",
    )
    parser.add_argument(
        "--required-headers",
        default=None,
        help="Comma-separated required headers; pass empty string or 'none' to disable.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a privacy-safe machine-readable summary.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse, validate, and type-map without writing to a live database.",
    )


def _build_parser() -> argparse.ArgumentParser:
    """Create the public inspection and ETL command parser."""
    parser = _JsonArgumentParser(
        prog="mhtml-etl-gateway",
        description="Inspect enterprise MHTML and load governed PostgreSQL tables.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_JsonArgumentParser,
    )

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

    load_parser = subparsers.add_parser("load", help="load one MHTML artifact")
    load_parser.add_argument("mhtml_path", type=str)
    _add_common_args(load_parser)
    load_parser.add_argument("--lineage-json", default=None)
    load_parser.add_argument("--ddl-out", default=None)

    batch_parser = subparsers.add_parser(
        "batch", help="load MHTML artifacts under a directory or glob"
    )
    batch_parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help="Directory, file, or glob (or set MHTML_ETL_SOURCE_DIR).",
    )
    _add_common_args(batch_parser)
    batch_parser.add_argument(
        "--continue-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    batch_parser.add_argument("--no-recursive", action="store_true")
    batch_parser.add_argument("--limit", type=int, default=None)
    return parser


def _write_error(error: MhtmlGatewayError) -> int:
    """Write one fixed JSON error object and return the conventional status."""
    print(
        json.dumps(error.to_dict(), ensure_ascii=False, sort_keys=True),
        file=sys.stderr,
    )
    return 2


def _safe_load_summary(result: dict[str, object]) -> dict[str, object]:
    """Return load fields that cannot expose row values or local paths."""
    queryable = result.get("queryable")
    row_count = queryable.get("db_row_count") if isinstance(queryable, dict) else None
    lineage = result.get("lineage")
    artifact_ref = lineage.get("source_artifact_path") if isinstance(lineage, dict) else None
    return {
        "artifact_ref": artifact_ref,
        "data_row_count": result.get("data_row_count"),
        "headers": result.get("headers", []),
        "inserted_rows": result.get("inserted_rows"),
        "queryable_row_count": row_count,
        "sha256": result.get("source_sha256"),
        "skipped": result.get("skipped"),
        "table_name": result.get("table_name"),
    }


def _run_inspect(args: argparse.Namespace) -> int:
    """Run the value-free inspection command."""
    try:
        limits = ParseLimits(max_source_bytes=args.max_source_bytes)
    except ValueError:
        return _write_error(MhtmlGatewayError(ErrorCode.INVALID_ARGUMENT))
    try:
        report = inspect_mhtml_file(args.source_path, limits=limits)
    except MhtmlGatewayError as error:
        return _write_error(error)

    indent = 2 if args.pretty else None
    print(
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=indent,
            separators=None if args.pretty else (",", ":"),
        )
    )
    return 0


def _run_load(args: argparse.Namespace) -> int:
    """Run one ETL load without reflecting source paths or row values."""
    path = Path(args.mhtml_path)
    if not path.is_file():
        print("error: source artifact is unavailable", file=sys.stderr)
        return 2

    required = _parse_required_headers(args.required_headers)
    on_duplicate: OnDuplicate = args.on_duplicate
    try:
        if not args.dry_run and not args.dsn:
            print("error: a database DSN is required unless --dry-run is used", file=sys.stderr)
            return 2
        result = convert_mhtml_to_postgres(
            path,
            dsn=None if args.dry_run else args.dsn,
            sink=None,
            table_name=args.table_name,
            column_mapping=args.column_mapping,
            lineage_json=args.lineage_json,
            on_duplicate=on_duplicate,
            required_headers=required,
        )
    except Exception:
        print("error: artifact load failed", file=sys.stderr)
        return 1

    summary = _safe_load_summary(result)
    if args.ddl_out:
        Path(args.ddl_out).write_text(result["ddl"] + "\n", encoding="utf-8")
    if args.as_json:
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"artifact_ref: {summary['artifact_ref']}")
        print(f"sha256: {summary['sha256']}")
        print(f"skipped: {summary['skipped']}")
        print(f"headers ({len(summary['headers'])}): {', '.join(summary['headers'][:12])}")
        print(f"data_rows: {summary['data_row_count']}")
        print(f"table: {summary['table_name']}")
        print(f"inserted_rows: {summary['inserted_rows']}")
        print(f"queryable_row_count: {summary['queryable_row_count']}")
    return 0


def _run_batch(args: argparse.Namespace) -> int:
    """Run a batch ETL load with aggregate, privacy-safe output only."""
    source = args.source or os.environ.get("MHTML_ETL_SOURCE_DIR")
    if not source:
        print("error: batch source is required", file=sys.stderr)
        return 2
    required = _parse_required_headers(args.required_headers)
    on_duplicate: OnDuplicate = args.on_duplicate
    if not args.dry_run and not args.dsn:
        print("error: a database DSN is required unless --dry-run is used", file=sys.stderr)
        return 2

    try:
        report = run_batch(
            source,
            dsn=None if args.dry_run else args.dsn,
            sink=None,
            table_name=args.table_name,
            column_mapping=args.column_mapping,
            on_duplicate=on_duplicate,
            continue_on_error=args.continue_on_error,
            recursive=not args.no_recursive,
            required_headers=required,
            limit=args.limit,
        )
    except Exception:
        print("error: batch load failed", file=sys.stderr)
        return 1

    summary = {
        "discovered": report.files_discovered,
        "failure_count": report.failure_count,
        "skipped_count": report.skipped_count,
        "success_count": report.success_count,
        "total_data_rows": report.total_data_rows,
        "total_inserted_rows": report.total_inserted_rows,
    }
    if args.as_json:
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 0 if report.failure_count == 0 else 1


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the CLI and return a conventional process status code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(arguments)
    except _ArgumentParserError:
        return _write_error(MhtmlGatewayError(ErrorCode.INVALID_ARGUMENT))

    if args.command == "inspect":
        return _run_inspect(args)
    if args.command == "load":
        return _run_load(args)
    if args.command == "batch":
        return _run_batch(args)
    return _write_error(MhtmlGatewayError(ErrorCode.INVALID_ARGUMENT))


if __name__ == "__main__":
    raise SystemExit(main())
