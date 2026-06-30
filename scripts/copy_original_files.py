#!/usr/bin/env python3
"""Copy original source files into a project's ori_files directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

try:
    from scripts.project_registry import resolve_project_path
except ModuleNotFoundError:
    from project_registry import resolve_project_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy original files from a source directory into ori_files."
    )
    parser.add_argument("project_name", help="Registered project name.")
    parser.add_argument("source_dir", help="Directory containing original files.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing destination files without prompting.",
    )
    return parser


def confirm_overwrite(destination: Path) -> bool:
    answer = input(
        f"Destination {destination} already exists. Overwrite it? [y/N]: "
    ).strip().lower()
    return answer in {"y", "yes"}


def copy_tree(source_dir: Path, destination_dir: Path, overwrite: bool) -> int:
    copied_files = 0

    for source_path in source_dir.rglob("*"):
        relative_path = source_path.relative_to(source_dir)
        destination_path = destination_dir / relative_path

        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path.exists() and not overwrite:
            if not confirm_overwrite(destination_path):
                continue

        shutil.copy2(source_path, destination_path)
        copied_files += 1

    return copied_files


def import_original_files(project_name: str, source_dir: str, overwrite: bool) -> tuple[Path, int]:
    project_dir = resolve_project_path(project_name).resolve()
    origin_dir = Path(source_dir).expanduser().resolve()

    if not origin_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {origin_dir}")
    if not origin_dir.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {origin_dir}")

    destination_dir = project_dir / "ori_files"
    destination_dir.mkdir(parents=True, exist_ok=True)

    copied_files = copy_tree(origin_dir, destination_dir, overwrite)
    return destination_dir, copied_files


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        destination_dir, copied_files = import_original_files(
            project_name=args.project_name,
            source_dir=args.source_dir,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, NotADirectoryError, KeyError) as exc:
        parser.error(str(exc))

    print(f"Copied {copied_files} files into {destination_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
