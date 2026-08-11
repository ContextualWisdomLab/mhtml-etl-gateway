"""CLI entry point for mhtml-etl-gateway."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from mhtml_etl_gateway.batch import run_batch
from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres
from mhtml_etl_gateway.postgres_loader import OnDuplicate


def _parse_required_headers(value: str | None) -> list[str] | None:
    if value is None:
        return None
    value = value.strip()
    if value == "" or value.lower() == "none":
        return []
    return [h.strip() for h in value.split(",") if h.strip()]


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dsn",
        default=os.environ.get("MHTML_ETL_DSN") or os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URI (or set MHTML_ETL_DSN / DATABASE_URL).",
    )
    p.add_argument(
        "--table-name",
        default=None,
        help="Override target table name (multiword snake_case applied).",
    )
    p.add_argument(
        "--column-mapping",
        "--column-comments",
        dest="column_mapping",
        default=None,
        help="Column mapping reference (.json, .csv, or .pptx) used for COMMENT ON COLUMN.",
    )
    p.add_argument(
        "--on-duplicate",
        choices=("skip", "replace"),
        default="skip",
        help="Idempotency: skip if sha256 already loaded (default), or replace rows for that sha.",
    )
    p.add_argument(
        "--required-headers",
        default=None,
        help="Comma-separated required headers (default: MANDT,GUID for ZCRHT811-shaped). "
        "Pass empty string or 'none' to disable.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON summary on stdout.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + validate + type-map only (in-memory sink; no live DB).",
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mhtml-etl-gateway",
        description="Convert SAP ALV / Excel Web Archive MHTML into PostgreSQL-typed tables.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    load_p = sub.add_parser("load", help="Load a single MHTML file.")
    load_p.add_argument("mhtml_path", type=str, help="Path to .MHTML / .mhtml artifact.")
    _add_common_args(load_p)
    load_p.add_argument("--lineage-json", default=None, help="Write lineage JSON path.")
    load_p.add_argument("--ddl-out", default=None, help="Write CREATE TABLE DDL path.")

    batch_p = sub.add_parser("batch", help="Load all MHTML files under a directory/glob.")
    batch_p.add_argument(
        "source",
        nargs="?",
        default=None,
        help="Directory, file, or glob (or set MHTML_ETL_SOURCE_DIR).",
    )
    _add_common_args(batch_p)
    batch_p.add_argument(
        "--continue-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Continue after per-file failures (default: true).",
    )
    batch_p.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subdirectories.",
    )
    batch_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N files (useful for smoke tests).",
    )
    return p


def _run_load(args: argparse.Namespace) -> int:
    path_str = getattr(args, "mhtml_path", None)
    if not path_str:
        print("error: mhtml_path is required", file=sys.stderr)
        return 2
    path = Path(path_str)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    required = _parse_required_headers(getattr(args, "required_headers", None))
    on_dup: OnDuplicate = args.on_duplicate  # type: ignore[assignment]

    try:
        if not args.dry_run and not args.dsn:
            print(
                "error: --dsn or MHTML_ETL_DSN/DATABASE_URL required "
                "(or pass --dry-run)",
                file=sys.stderr,
            )
            return 2
        result = convert_mhtml_to_postgres(
            path,
            dsn=None if args.dry_run else args.dsn,
            sink=None,
            table_name=args.table_name,
            column_mapping=args.column_mapping,
            lineage_json=args.lineage_json,
            on_duplicate=on_dup,
            required_headers=required,
        )

        if getattr(args, "ddl_out", None):
            Path(args.ddl_out).write_text(result["ddl"] + "\n", encoding="utf-8")

        if args.as_json:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            print("source: [redacted]")
            print(f"artifact_ref: {result['lineage']['source_artifact_path']}")
            print(f"sha256: {result['source_sha256']}")
            print(f"skipped: {result.get('skipped')}")
            print(
                f"headers ({len(result['headers'])}): {', '.join(result['headers'][:12])}"
                + ("..." if len(result["headers"]) > 12 else "")
            )
            print(f"data_rows: {result['data_row_count']}")
            print(f"table: {result['table_name']}")
            print(f"inserted_rows: {result['inserted_rows']}")
            print(f"queryable_row_count: {result['queryable'].get('db_row_count')}")
            if result.get("catalog"):
                print(f"catalog_status: {result['catalog'].get('status')}")
            if result.get("lineage_json"):
                print(f"lineage_json: {result['lineage_json']}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run_batch(args: argparse.Namespace) -> int:
    source = args.source or os.environ.get("MHTML_ETL_SOURCE_DIR")
    if not source:
        print(
            "error: batch source required (positional or MHTML_ETL_SOURCE_DIR)",
            file=sys.stderr,
        )
        return 2

    required = _parse_required_headers(getattr(args, "required_headers", None))
    on_dup: OnDuplicate = args.on_duplicate  # type: ignore[assignment]

    if not args.dry_run and not args.dsn:
        print(
            "error: --dsn or MHTML_ETL_DSN/DATABASE_URL required (or --dry-run)",
            file=sys.stderr,
        )
        return 2

    try:
        report = run_batch(
            source,
            dsn=None if args.dry_run else args.dsn,
            sink=None,
            table_name=args.table_name,
            column_mapping=args.column_mapping,
            on_duplicate=on_dup,
            continue_on_error=args.continue_on_error,
            recursive=not args.no_recursive,
            required_headers=required,
            limit=args.limit,
        )
        payload = report.to_dict()
        if args.as_json:
            print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"source: {report.source}")
            print(f"discovered: {report.files_discovered}")
            print(f"success: {report.success_count}")
            print(f"failure: {report.failure_count}")
            print(f"skipped_dup: {report.skipped_count}")
            print(f"total_data_rows: {report.total_data_rows}")
            print(f"total_inserted_rows: {report.total_inserted_rows}")
            for fr in report.results:
                status = "OK" if fr.ok else "FAIL"
                if fr.skipped:
                    status = "SKIP"
                print(
                    f"  [{status}] {fr.path} rows={fr.rows} inserted={fr.inserted_rows}"
                    + (f" err={fr.error}" if fr.error else "")
                )
        return 0 if report.failure_count == 0 else 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    argv_list: list[str] = list(sys.argv[1:] if argv is None else argv)
    known = {"load", "batch", "-h", "--help"}
    # Backward compatible: bare path → load <path>
    if argv_list and argv_list[0] not in known and not argv_list[0].startswith("-"):
        argv_list = ["load", *argv_list]
    elif not argv_list:
        argv_list = ["--help"]

    parser = _build_parser()
    args = parser.parse_args(argv_list)

    if args.command == "batch":
        return _run_batch(args)
    if args.command == "load":
        return _run_load(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
