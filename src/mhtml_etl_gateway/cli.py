"""CLI entry point for mhtml-etl-gateway."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres, extract_table, infer_schema_for_extract


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mhtml-etl-gateway",
        description="Convert SAP ALV / Excel Web Archive MHTML into PostgreSQL-typed tables.",
    )
    p.add_argument("mhtml_path", type=str, help="Path to .MHTML / .mhtml artifact (immutable).")
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
        "--lineage-json",
        default=None,
        help="Write lineage metadata JSON to this path.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + type-map only; print DDL and skip live DB (uses in-memory sink).",
    )
    p.add_argument(
        "--ddl-out",
        default=None,
        help="Write inferred CREATE TABLE DDL to this path.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON summary on stdout.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    path = Path(args.mhtml_path)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        if args.dry_run and not args.dsn:
            extracted = extract_table(path)
            schema = infer_schema_for_extract(extracted, table_name=args.table_name)
            result = convert_mhtml_to_postgres(
                path,
                sink=None,
                table_name=args.table_name,
                lineage_json=args.lineage_json,
            )
        else:
            if not args.dry_run and not args.dsn:
                print(
                    "error: --dsn or MHTML_ETL_DSN/DATABASE_URL required "
                    "(or pass --dry-run for offline parse/type map)",
                    file=sys.stderr,
                )
                return 2
            result = convert_mhtml_to_postgres(
                path,
                dsn=None if args.dry_run else args.dsn,
                table_name=args.table_name,
                lineage_json=args.lineage_json,
            )

        if args.ddl_out:
            Path(args.ddl_out).write_text(result["ddl"] + "\n", encoding="utf-8")

        if args.as_json:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"source: {path}")
            print(f"sha256: {result['source_sha256']}")
            print(f"headers ({len(result['headers'])}): {', '.join(result['headers'][:12])}"
                  + ("..." if len(result["headers"]) > 12 else ""))
            print(f"data_rows: {result['data_row_count']}")
            print(f"table: {result['table_name']}")
            print(f"inserted_rows: {result['inserted_rows']}")
            print(f"queryable_row_count: {result['queryable'].get('db_row_count', result['inserted_rows'])}")
            if result.get("lineage_json"):
                print(f"lineage_json: {result['lineage_json']}")
            print("--- type map (sample) ---")
            for i, (src, pg) in enumerate(result["schema"].items()):
                if i >= 12:
                    print("...")
                    break
                print(f"  {src} -> {pg}")
            print("--- ddl ---")
            print(result["ddl"])
        return 0
    except Exception as exc:  # fail closed with non-zero exit
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
