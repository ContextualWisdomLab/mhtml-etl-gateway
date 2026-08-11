"""Batch directory / glob ingestion over the single-file pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from mhtml_etl_gateway.lineage import artifact_reference
from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres
from mhtml_etl_gateway.postgres_loader import OnDuplicate, RowSink

MHTML_SUFFIXES = {".mhtml", ".MHTML"}


class BatchError(RuntimeError):
    """Sanitized batch failure that never carries an operator input path."""


@dataclass
class FileResult:
    path: str
    ok: bool
    sha256: str | None = None
    rows: int = 0
    inserted_rows: int = 0
    skipped: bool = False
    error: str | None = None
    table_name: str | None = None


@dataclass
class BatchReport:
    source: str
    files_discovered: int
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    total_data_rows: int = 0
    total_inserted_rows: int = 0
    results: list[FileResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def discover_mhtml_files(
    source: str | Path,
    *,
    recursive: bool = True,
) -> list[Path]:
    """Discover .MHTML / .mhtml files under a directory or expand a single file/glob."""
    root = Path(source)
    if root.is_file():
        return [root]
    if not root.exists():
        # pathlib.glob does not accept absolute patterns; peel to an existing parent.
        pattern = str(source)
        matches: list[Path] = []
        if Path(pattern).is_absolute():
            p = Path(pattern)
            # Support /base/**/*.mhtml style by walking up to an existing directory.
            cur, parts = p, []
            while str(cur) not in ("", "/") and not cur.exists():
                parts.append(cur.name)
                cur = cur.parent
            if cur.exists() and parts:
                rel = "/".join(reversed(parts))
                matches = sorted(cur.glob(rel))
            elif p.parent.exists():
                matches = sorted(p.parent.glob(p.name))
        else:
            matches = sorted(Path().glob(pattern))
        return [
            p
            for p in matches
            if p.is_file() and p.suffix.lower() == ".mhtml"
        ]

    paths: list[Path] = []
    iterator = root.rglob("*") if recursive else root.glob("*")
    for p in iterator:
        if p.is_file() and p.suffix.lower() == ".mhtml":
            paths.append(p)
    return sorted(paths)


def run_batch(
    source: str | Path,
    *,
    dsn: str | None = None,
    sink: RowSink | None = None,
    table_name: str | None = None,
    column_mapping: str | Path | None = None,
    on_duplicate: OnDuplicate = "skip",
    continue_on_error: bool = True,
    recursive: bool = True,
    required_headers: Sequence[str] | None = None,
    limit: int | None = None,
) -> BatchReport:
    """Process all MHTML files under ``source`` with the single-file pipeline."""
    files = discover_mhtml_files(source, recursive=recursive)
    if limit is not None:
        files = files[: max(0, limit)]

    # Keep operator-provided directory names out of reports and JSON output.
    report = BatchReport(source="operator-supplied-directory", files_discovered=len(files))
    shared_sink = sink
    own_pg = False
    if shared_sink is None and dsn:
        from mhtml_etl_gateway.postgres_loader import PsycopgSink

        shared_sink = PsycopgSink(dsn)
        own_pg = True

    try:
        for index, path in enumerate(files, 1):
            fr = FileResult(path=f"file-{index:04d}", ok=False)
            try:
                result = convert_mhtml_to_postgres(
                    path,
                    dsn=None if shared_sink is not None else dsn,
                    sink=shared_sink,
                    table_name=table_name,
                    column_mapping=column_mapping,
                    on_duplicate=on_duplicate,
                    required_headers=required_headers,
                )
                fr.ok = True
                fr.sha256 = result["source_sha256"]
                fr.path = artifact_reference(result["source_sha256"])
                fr.rows = int(result["data_row_count"])
                fr.inserted_rows = int(result["inserted_rows"])
                fr.skipped = bool(result.get("skipped"))
                fr.table_name = result.get("table_name")
                report.success_count += 1
                if fr.skipped:
                    report.skipped_count += 1
                report.total_data_rows += fr.rows
                report.total_inserted_rows += fr.inserted_rows
            except Exception as exc:
                fr.ok = False
                # Exception messages can contain the real input path. Preserve
                # the failure class without leaking operator data.
                fr.error = type(exc).__name__
                report.failure_count += 1
                # Reset aborted transaction so later files can continue.
                rollback = getattr(shared_sink, "rollback", None)
                if callable(rollback):
                    try:
                        rollback()
                    except Exception as rb_exc:
                        # Best-effort: connection may already be closed mid-batch.
                        fr.error = f"{fr.error}; rollback_failed={type(rb_exc).__name__}"
                if not continue_on_error:
                    report.results.append(fr)
                    raise BatchError("batch ingestion failed") from None
            report.results.append(fr)
    finally:
        if own_pg and shared_sink is not None:
            close = getattr(shared_sink, "close", None)
            if callable(close):
                close()

    return report
