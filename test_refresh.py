"""Tests for refresh.py - the normaliser's contract, both directions per behaviour."""

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from refresh import is_date_column, main, normalise_date


def write_csv(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def read_rows(path: Path) -> list:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_duplicates_are_dropped_first_occurrence_wins(tmp_path):
    source = write_csv(tmp_path / "data.csv",
                       "id,item\n1,apple\n2,pear\n1,apple\n")
    main([str(source)])
    assert read_rows(source) == [["id", "item"], ["1", "apple"], ["2", "pear"]]


def test_dates_in_date_columns_become_iso(tmp_path):
    source = write_csv(tmp_path / "data.csv",
                       "id,order_date,note\n1,25/12/2026,x\n2,12/31/2026,y\n")
    main([str(source)])
    rows = read_rows(source)
    assert rows[1][1] == "2026-12-25"
    assert rows[2][1] == "2026-12-31"


def test_an_unparseable_date_passes_through_untouched(tmp_path):
    source = write_csv(tmp_path / "data.csv", "id,order_date\n1,not-a-date\n")
    main([str(source)])
    assert read_rows(source)[1][1] == "not-a-date"


def test_rows_are_sorted_so_the_file_is_diff_stable(tmp_path):
    source = write_csv(tmp_path / "data.csv", "id,item\n9,zeta\n1,alpha\n")
    main([str(source)])
    assert read_rows(source) == [["id", "item"], ["1", "alpha"], ["9", "zeta"]]


def test_a_bak_is_kept_when_rewriting_in_place(tmp_path):
    source = write_csv(tmp_path / "data.csv", "id,item\n1,apple\n1,apple\n")
    original = source.read_text(encoding="utf-8")
    main([str(source)])
    assert source.with_suffix(".csv.bak").read_text(encoding="utf-8") == original


def test_check_changes_nothing_and_reports(tmp_path):
    source = write_csv(tmp_path / "data.csv", "id,item\n1,apple\n1,apple\n")
    original = source.read_text(encoding="utf-8")
    code = main(["--check", str(source)])
    assert code == 0
    assert source.read_text(encoding="utf-8") == original, "--check touches nothing"
    assert not source.with_suffix(".csv.bak").exists()


def test_output_writes_a_copy_and_leaves_the_original(tmp_path):
    source = write_csv(tmp_path / "data.csv", "id,item\n9,zeta\n1,alpha\n1,alpha\n")
    out = tmp_path / "out"
    main(["--output", str(out), str(source)])
    assert read_rows(out / "data.csv") == [["id", "item"], ["1", "alpha"], ["9", "zeta"]]
    assert read_rows(source) == [["id", "item"], ["9", "zeta"], ["1", "alpha"], ["1", "alpha"]]


def test_a_directory_is_expanded_to_its_csv_children(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    write_csv(folder / "a.csv", "id,item\n1,apple\n")
    write_csv(folder / "b.txt", "not a csv\n")
    main([str(folder)])
    assert (folder / "a.csv.bak").exists()
    assert not (folder / "b.txt.bak").exists(), "b.txt is not a csv: untouched"


def test_short_rows_are_padded_to_the_header(tmp_path):
    source = write_csv(tmp_path / "data.csv", "id,item,price\n1,apple\n")
    main([str(source)])
    assert read_rows(source)[1] == ["1", "apple", ""]


def test_no_files_found_is_an_error(tmp_path):
    import contextlib
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        code = main([str(tmp_path / "empty")])
    assert code == 1
    assert "no CSV files found" in buffer.getvalue()


def test_the_date_column_rule():
    assert is_date_column("order_date") and is_date_column("Date")
    assert not is_date_column("date_idea") and not is_date_column("update")


def test_the_date_formats_the_tool_claims(tmp_path):
    for raw, expected in (("2026-12-25", "2026-12-25"), ("25/12/2026", "2026-12-25"),
                          ("12/31/2026", "2026-12-31"), ("2026/12/25", "2026-12-25"),
                          ("25-12-2026", "2026-12-25")):
        assert normalise_date(raw) == expected, raw
