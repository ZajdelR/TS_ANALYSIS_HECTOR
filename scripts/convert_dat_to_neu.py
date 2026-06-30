#!/usr/bin/env python3
"""Convert fixed-width DAT files into NEU time-series files."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.project_registry import resolve_project_path
except ModuleNotFoundError:
    from project_registry import resolve_project_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert DAT files from ori_files into NEU files in ori_files."
    )
    parser.add_argument("project_name", help="Registered project name.")
    parser.add_argument(
        "--filename",
        help="Convert only one DAT file from ori_files instead of all *.dat files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing NEU files without prompting.",
    )
    return parser


def confirm_overwrite(destination: Path) -> bool:
    answer = input(
        f"Destination {destination} already exists. Overwrite it? [y/N]: "
    ).strip().lower()
    return answer in {"y", "yes"}


def to_year_fraction(timestamp: datetime) -> float:
    year_start = datetime(timestamp.year, 1, 1, tzinfo=timezone.utc)
    next_year_start = datetime(timestamp.year + 1, 1, 1, tzinfo=timezone.utc)
    elapsed = (timestamp - year_start).total_seconds()
    duration = (next_year_start - year_start).total_seconds()
    return timestamp.year + elapsed / duration


def parse_dat_line(line: str) -> tuple[float, float, float, float] | None:
    columns = line.split()
    if len(columns) < 10:
        return None

    try:
        timestamp = datetime.strptime(
            f"{columns[2]} {columns[3]}", "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        north = float(columns[7])
        east = float(columns[8])
        up = float(columns[9])
    except ValueError:
        return None

    return to_year_fraction(timestamp), north, east, up


def convert_dat_file(source_path: Path, destination_path: Path, overwrite: bool) -> int:
    if destination_path.exists() and not overwrite:
        if not confirm_overwrite(destination_path):
            return 0

    converted_rows = 0
    with source_path.open(encoding="utf-8") as source, destination_path.open(
        "w", encoding="utf-8"
    ) as destination:
        destination.write("# year_fraction north[m] east[m] up[m]\n")

        for line_number, line in enumerate(source):
            if line_number == 0:
                continue

            parsed = parse_dat_line(line)
            if parsed is None:
                continue

            year_fraction, north, east, up = parsed
            destination.write(
                f"{year_fraction:.10f} {north:.6f} {east:.6f} {up:.6f}\n"
            )
            converted_rows += 1

    return converted_rows


def collect_dat_files(origin_dir: Path, filename: str | None) -> list[Path]:
    if filename:
        source_path = origin_dir / filename
        if not source_path.exists():
            raise FileNotFoundError(f"DAT file does not exist: {source_path}")
        if source_path.suffix.lower() != ".dat":
            raise ValueError(f"Expected a .dat file, got: {source_path.name}")
        return [source_path]

    return sorted(path for path in origin_dir.glob("*.dat") if path.is_file())


def convert_project_dat_files(
    project_name: str,
    filename: str | None,
    overwrite: bool,
) -> tuple[Path, int, int]:
    project_dir = resolve_project_path(project_name).resolve()
    origin_dir = project_dir / "ori_files"
    destination_dir = origin_dir

    if not origin_dir.exists():
        raise FileNotFoundError(f"Origin directory does not exist: {origin_dir}")

    source_files = collect_dat_files(origin_dir, filename)
    if not source_files:
        raise FileNotFoundError(f"No .dat files found in {origin_dir}")

    destination_dir.mkdir(parents=True, exist_ok=True)

    converted_files = 0
    converted_rows = 0
    for source_path in source_files:
        destination_path = destination_dir / f"{source_path.stem}.neu"
        rows_in_file = convert_dat_file(source_path, destination_path, overwrite)
        if rows_in_file > 0:
            converted_files += 1
            converted_rows += rows_in_file

    return destination_dir, converted_files, converted_rows


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        destination_dir, converted_files, converted_rows = convert_project_dat_files(
            project_name=args.project_name,
            filename=args.filename,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        parser.error(str(exc))

    print(
        f"Converted {converted_files} file(s) with {converted_rows} row(s) into "
        f"{destination_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
