#!/usr/bin/env python3
"""Convert project NEU files into HECTOR MOM component files."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

try:
    from scripts.project_registry import resolve_project_path
except ModuleNotFoundError:
    from project_registry import resolve_project_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert NEU files from ori_files into MOM files in raw_files."
    )
    parser.add_argument("project_name", help="Registered project name.")
    parser.add_argument(
        "--filename",
        help="Convert only one NEU file from ori_files instead of all *.neu files.",
    )
    parser.add_argument(
        "--sampling-period",
        type=float,
        default=1.0,
        help="Sampling period written to the MOM header.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing MOM files without prompting.",
    )
    return parser


def get_mjd(year_fraction: float) -> float:
    year = int(math.floor(year_fraction))
    month = 1
    day = 1
    mjd = (
        367 * year
        - int(7 * (year + int((month + 9) / 12)) / 4)
        + int(275 * month / 9)
        + day
        + 1721014
        - 2400001
    )
    mjd += 365.0 * (year_fraction - year)
    return mjd


def confirm_overwrite(destination: Path) -> bool:
    answer = input(
        f"Destination {destination} already exists. Overwrite it? [y/N]: "
    ).strip().lower()
    return answer in {"y", "yes"}


def collect_neu_files(origin_dir: Path, filename: str | None) -> list[Path]:
    if filename:
        source_path = origin_dir / filename
        if not source_path.exists():
            raise FileNotFoundError(f"NEU file does not exist: {source_path}")
        if source_path.suffix.lower() != ".neu":
            raise ValueError(f"Expected a .neu file, got: {source_path.name}")
        return [source_path]

    return sorted(path for path in origin_dir.glob("*.neu") if path.is_file())


def prepare_output_paths(
    destination_dir: Path,
    station_name: str,
    overwrite: bool,
) -> list[Path] | None:
    output_paths = [destination_dir / f"{station_name}_{index}.mom" for index in range(3)]

    if overwrite:
        return output_paths

    for output_path in output_paths:
        if output_path.exists() and not confirm_overwrite(output_path):
            return None

    return output_paths


def convert_neu_file(
    source_path: Path,
    destination_dir: Path,
    sampling_period: float,
    overwrite: bool,
) -> int:
    station_name = source_path.stem
    output_paths = prepare_output_paths(destination_dir, station_name, overwrite)
    if output_paths is None:
        return 0

    output_files = [path.open("w", encoding="utf-8") for path in output_paths]
    try:
        for output_file in output_files:
            output_file.write(f"# sampling period {sampling_period}\n")

        first_values: tuple[float, float, float] | None = None
        converted_rows = 0
        with source_path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip() or line.startswith("#"):
                    continue

                columns = line.split()
                if len(columns) < 4:
                    continue

                year_fraction = float(columns[0])
                north = float(columns[1])
                east = float(columns[2])
                up = float(columns[3])

                if first_values is None:
                    first_values = (east, north, up)

                east_zero, north_zero, up_zero = first_values
                east_mm = 1000.0 * (east - east_zero)
                north_mm = 1000.0 * (north - north_zero)
                up_mm = 1000.0 * (up - up_zero)
                mjd = get_mjd(year_fraction)

                output_files[0].write(f"{mjd:8.1f} {east_mm:8.2f}\n")
                output_files[1].write(f"{mjd:8.1f} {north_mm:8.2f}\n")
                output_files[2].write(f"{mjd:8.1f} {up_mm:8.2f}\n")
                converted_rows += 1
    finally:
        for output_file in output_files:
            output_file.close()

    return converted_rows


def convert_project_neu_files(
    project_name: str,
    filename: str | None,
    sampling_period: float,
    overwrite: bool,
) -> tuple[Path, int, int]:
    project_dir = resolve_project_path(project_name).resolve()
    origin_dir = project_dir / "ori_files"
    destination_dir = project_dir / "raw_files"

    if not origin_dir.exists():
        raise FileNotFoundError(f"Origin directory does not exist: {origin_dir}")

    source_files = collect_neu_files(origin_dir, filename)
    if not source_files:
        raise FileNotFoundError(f"No .neu files found in {origin_dir}")

    destination_dir.mkdir(parents=True, exist_ok=True)

    converted_files = 0
    converted_rows = 0
    for source_path in source_files:
        rows_in_file = convert_neu_file(
            source_path=source_path,
            destination_dir=destination_dir,
            sampling_period=sampling_period,
            overwrite=overwrite,
        )
        if rows_in_file > 0:
            converted_files += 1
            converted_rows += rows_in_file

    return destination_dir, converted_files, converted_rows


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        destination_dir, converted_files, converted_rows = convert_project_neu_files(
            project_name=args.project_name,
            filename=args.filename,
            sampling_period=args.sampling_period,
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
