"""Helpers for reading the generated project config file."""

from __future__ import annotations

from pathlib import Path

try:
    from scripts.project_registry import resolve_project_path
except ModuleNotFoundError:
    from project_registry import resolve_project_path


def _parse_scalar(value: str) -> object:
    text = value.strip()
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text in {"true", "false"}:
        return text == "true"
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def load_project_config(project_name: str) -> tuple[Path, dict[str, dict[str, object]]]:
    project_dir = resolve_project_path(project_name).resolve()
    config_path = project_dir / "config" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Project config does not exist: {config_path}")

    config: dict[str, dict[str, object]] = {}
    current_section: str | None = None
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith("  "):
            if current_section is None:
                continue
            key, value = raw_line.strip().split(":", 1)
            config[current_section][key] = _parse_scalar(value)
            continue

        key, value = raw_line.split(":", 1)
        if value.strip():
            config[key] = {"value": _parse_scalar(value)}
            current_section = None
        else:
            config[key] = {}
            current_section = key

    return project_dir, config
