from __future__ import annotations

from pathlib import Path

from mhtml_etl_gateway.batch import discover_mhtml_files, run_batch
from mhtml_etl_gateway.postgres_loader import InMemorySink


def test_discover_and_batch_multi_fixture(tmp_path: Path, sample_mhtml_path: Path) -> None:
    # Create a mini multi-file corpus from the fixture (3 copies with distinct names)
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for i in range(3):
        dest = corpus / f"ZCRHT811_export_part{i}.MHTML"
        dest.write_bytes(sample_mhtml_path.read_bytes())

    found = discover_mhtml_files(corpus)
    assert len(found) == 3

    sink = InMemorySink()
    report = run_batch(
        corpus,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="skip",
    )
    assert report.files_discovered == 3
    assert report.success_count == 3
    assert report.failure_count == 0
    assert report.total_data_rows > 0
    # Three distinct sha? same content → same sha → only first inserts, others skip
    # All same bytes → same sha256 → first load inserts, next two skip
    assert report.skipped_count == 2
    assert sink.count_rows("zcrht811_export_rows") == report.results[0].rows
    assert all(fr.ok for fr in report.results)


def test_batch_distinct_content_all_insert(tmp_path: Path, sample_mhtml_path: Path) -> None:
    corpus = tmp_path / "corpus2"
    corpus.mkdir()
    base = sample_mhtml_path.read_bytes()
    for i in range(3):
        # Mutate a comment so sha differs but table still valid
        mutated = base + f"\n<!-- batch-unique-{i} -->\n".encode()
        (corpus / f"file_{i}.MHTML").write_bytes(mutated)

    sink = InMemorySink()
    report = run_batch(
        corpus,
        sink=sink,
        table_name="zcrht811_export_rows",
        on_duplicate="skip",
    )
    assert report.success_count == 3
    assert report.skipped_count == 0
    assert report.total_inserted_rows == sink.count_rows("zcrht811_export_rows")
    assert report.total_inserted_rows >= 3
