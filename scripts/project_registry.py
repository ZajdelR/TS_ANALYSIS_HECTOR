"""Helpers for tracking project names and their filesystem locations."""

from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECT_REGISTRY_PATH = ROOT_DIR / "project_registry.json"


def load_project_registry() -> dict[str, str]:
    if not PROJECT_REGISTRY_PATH.exists():
        return {}

    return json.loads(PROJECT_REGISTRY_PATH.read_text(encoding="utf-8"))


def save_project_registry(registry: dict[str, str]) -> None:
    PROJECT_REGISTRY_PATH.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def register_project(
    project_name: str,
    project_dir: Path,
    overwrite_existing: bool = False,
) -> None:
    registry = load_project_registry()
    project_path = str(project_dir.resolve())
    existing_path = registry.get(project_name)

    if existing_path and existing_path != project_path and not overwrite_existing:
        raise FileExistsError(
            f"Project '{project_name}' is already registered at {existing_path}. "
            "Use --overwrite-registry to replace it."
        )

    registry[project_name] = project_path
    save_project_registry(registry)


def resolve_project_path(project_name: str) -> Path:
    registry = load_project_registry()

    if project_name not in registry:
        raise KeyError(f"Project '{project_name}' is not registered.")

    return Path(registry[project_name])
