#!/usr/bin/env python3
"""Normalise the CSVs of a long collection project: dedupe, ISO dates, sorted rows.

A collection project's CSVs drift: duplicate rows from retries, dates in whatever format the
day's export used, row order that shuffles with every merge. This tool rewrites them in place (a
`.bak` beside each) so the files diff cleanly afterwards.

Usage:
    python refresh.py <path>... [--check] [--output DIR]

`<path>` is a CSV file or a directory (its `.csv` children, non-recursive). `--check` reports what
would change and touches nothing. `--output DIR` writes normalised copies there instead of beside
the originals.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import datetime
from pathlib import Path

DATE_SUFFIXES = ("_date",)
DATE_NAMES = ("date",)


def is_date_column(name: str) -> bool:
    lowered = name.strip().lower()
    return lowered in DATE_NAMES or lowered.endswith(DATE_SUFFIXES)


def normalise_date(value: str) -> str:
    """Rewrite a date cell to ISO YYYY-MM-DD; unparseable cells pass through untouched."""
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def normalise_rows(header: list[str], rows: list[list[str]]) -> tuple[list[str], list[list[str]], int]:
    """Return (header, unique sorted rows, dropped duplicate count)."""
    width = len(header)
    date_columns = [index for index, name in enumerate(header) if is_date_column(name)]
    fixed = []
    for row in rows:
        row = list(row) + [""] * (width - len(row))
        fixed.append(row[:width])
    for row in fixed:
        for index in date_columns:
            row[index] = normalise_date(row[index])
    seen = set()
    unique = []
    for row in fixed:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    unique.sort()
    return header, unique, len(fixed) - len(unique)


def normalise_file(path: Path, output: Path | None, check_only: bool) -> str:
    """Normalise one CSV; returns a one-line report of what happened (or would, under --check)."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return f"{path}: empty, left alone"
    header, unique, dropped = normalise_rows(rows[0], rows[1:])

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(unique)
    body = buffer.getvalue()

    if check_only:
        return (f"{path}: would drop {dropped} duplicate(s), sort {len(unique)} row(s)")
    target = (output / path.name) if output else path
    target.parent.mkdir(parents=True, exist_ok=True)
    if output is None:
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_bytes(path.read_bytes())
    target.write_text(body, encoding="utf-8")
    return f"{path}: dropped {dropped} duplicate(s), sorted {len(unique)} row(s) -> {target}"


def collect_csvs(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.csv")))
        elif path.exists():
            files.append(path)
        else:
            print(f"skipping {path}: no such path", file=sys.stderr)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("paths", nargs="+", type=Path, help="CSV files or directories of them")
    parser.add_argument("--check", action="store_true", help="Report, change nothing")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write normalised copies here instead of beside the originals")
    args = parser.parse_args(argv)

    files = collect_csvs(args.paths)
    if not files:
        print("no CSV files found", file=sys.stderr)
        return 1
    for path in files:
        print(normalise_file(path, args.output, args.check))
    return 0


if __name__ == "__main__":
    sys.exit(main())
