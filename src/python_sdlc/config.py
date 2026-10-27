"""Read python-sdlc settings from ``pyproject.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TABLE = "python-sdlc"


class ConfigError(Exception):
    """Raised when ``pyproject.toml`` or its ``[tool.python-sdlc]`` table is bad."""


def _default_paths() -> list[str]:
    return ["src", "tests"]


def _default_mypy_paths() -> list[str]:
    return ["src"]


@dataclass(frozen=True)
class LintConfig:
    """Paths each lint step operates on.

    Attributes:
        paths: Targets for black and ruff.
        mypy_paths: Targets for mypy.
        test_paths: Targets for pytest. Empty means pass no paths and let the
            project's own pytest configuration decide.
    """

    paths: list[str] = field(default_factory=_default_paths)
    mypy_paths: list[str] = field(default_factory=_default_mypy_paths)
    test_paths: list[str] = field(default_factory=list)


def _string_list(table: dict[str, Any], key: str, default: list[str]) -> list[str]:
    """Return ``table[key]`` as a list of strings, or ``default`` if absent."""
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"[tool.{TABLE}] {key} must be a list of strings")
    return list(value)


def load_config(directory: Path | None = None) -> LintConfig:
    """Load lint settings from ``pyproject.toml`` in ``directory``.

    A missing file or missing ``[tool.python-sdlc]`` table yields the defaults.

    Raises:
        ConfigError: If the file is not valid TOML or a value has the wrong type.
    """
    pyproject = (directory or Path.cwd()) / "pyproject.toml"
    if not pyproject.is_file():
        return LintConfig()

    try:
        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"could not parse {pyproject}: {exc}") from exc

    table = data.get("tool", {}).get(TABLE, {})
    if not isinstance(table, dict):
        raise ConfigError(f"[tool.{TABLE}] must be a table")

    defaults = LintConfig()
    return LintConfig(
        paths=_string_list(table, "paths", defaults.paths),
        mypy_paths=_string_list(table, "mypy_paths", defaults.mypy_paths),
        test_paths=_string_list(table, "test_paths", defaults.test_paths),
    )
