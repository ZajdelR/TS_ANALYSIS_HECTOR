#!/usr/bin/env python3
"""Create a new HECTOR analysis project scaffold."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

try:
    from scripts.project_registry import register_project
except ModuleNotFoundError:
    from project_registry import register_project

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"

DEFAULT_SUBDIRECTORIES = (
    "config",
    "ori_files",
    "raw_files",
    "obs_files",
    "pre_files",
    "mom_files",
    "sea_files",
    "fil_files",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a new time-series analysis project for HECTOR."
    )
    parser.add_argument("project_name", help="Project directory name inside projects/.")
    parser.add_argument(
        "--project-root",
        default=str(PROJECTS_DIR),
        help="Base directory where the project directory will be created.",
    )
    parser.add_argument(
        "--hector-home",
        default="/home/radek/app/hector",
        help="Base path that contains HECTOR executables and resources.",
    )
    parser.add_argument(
        "--overwrite-registry",
        action="store_true",
        help="Replace an existing project-name to path mapping in the registry.",
    )
    return parser


def validate_project_name(project_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", project_name):
        raise ValueError(
            "Project name must start with an alphanumeric character and contain "
            "only letters, digits, dots, underscores, or hyphens."
        )
    return project_name


def render_yaml(project_name: str, project_dir: Path, hector_home: Path) -> str:
    return "\n".join(
        (
            f'project_name: "{project_name}"',
            "analysis:",
            "  reference_frame: \"IGS14\"",
            "  sampling_period_days: 1.0",
            "  noise_model: \"plwn\"",
            "  estimate_offsets: true",
            "  estimate_seasonal_signals: true",
            "  use_outlier_detection: true",
            "paths:",
            f'  project_root: "{project_dir}"',
            '  ori_files_dir: "ori_files"',
            '  raw_files_dir: "raw_files"',
            '  obs_files_dir: "obs_files"',
            '  pre_files_dir: "pre_files"',
            '  mom_files_dir: "mom_files"',
            '  sea_files_dir: "sea_files"',
            '  fil_files_dir: "fil_files"',
            f'  hector_home: "{hector_home}"',
            f'  hector_estimatetrend: "{hector_home / "estimatetrend"}"',
            f'  hector_removeoutliers: "{hector_home / "removeoutliers"}"',
            f'  hector_estimatespectrum: "{hector_home / "estimatespectrum"}"',
            "files:",
            '  station_timeseries: ""',
            '  offsets_catalog: ""',
            '  postseismic_catalog: ""',
            "notes:",
            '  description: ""',
            '  created_by: "init_project.py"',
            "",
        )
    )


def confirm_reinitialize(project_dir: Path) -> bool:
    prompt = (
        f"Project directory {project_dir} already exists. "
        "Remove it and reinitialize? [y/N]: "
    )
    answer = input(prompt).strip().lower()
    return answer in {"y", "yes"}


def initialize_project(
    project_name: str,
    project_root: str,
    hector_home: str,
    overwrite_registry: bool,
) -> Path:
    validate_project_name(project_name)

    base_dir = Path(project_root).expanduser().resolve()
    project_dir = base_dir / project_name

    if project_dir.exists():
        if not confirm_reinitialize(project_dir):
            raise FileExistsError(f"Project initialization cancelled for {project_dir}.")
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True, exist_ok=True)

    for relative_dir in DEFAULT_SUBDIRECTORIES:
        (project_dir / relative_dir).mkdir(parents=True, exist_ok=True)

    config_path = project_dir / "config" / "config.yaml"
    config_path.write_text(
        render_yaml(project_name, project_dir, Path(hector_home).expanduser()),
        encoding="utf-8",
    )
    register_project(
        project_name=project_name,
        project_dir=project_dir,
        overwrite_existing=overwrite_registry,
    )
    return project_dir


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        project_dir = initialize_project(
            project_name=args.project_name,
            project_root=args.project_root,
            hector_home=args.hector_home,
            overwrite_registry=args.overwrite_registry,
        )
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))

    print(f"Initialized project at {project_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
