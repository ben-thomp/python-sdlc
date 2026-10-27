"""Tests for python_sdlc.config."""

from pathlib import Path

import pytest

from python_sdlc.config import ConfigError, LintConfig, load_config


def test_defaults_without_pyproject(tmp_path: Path) -> None:
    assert load_config(tmp_path) == LintConfig(
        paths=["src", "tests"], mypy_paths=["src"], test_paths=[]
    )


def test_defaults_without_table(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert load_config(tmp_path) == LintConfig()


def test_overrides(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.python-sdlc]\npaths = ["lib"]\ntest_paths = ["t"]\n'
    )
    config = load_config(tmp_path)
    assert config.paths == ["lib"]
    assert config.mypy_paths == ["src"]
    assert config.test_paths == ["t"]


def test_malformed_toml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.python-sdlc\n")
    with pytest.raises(ConfigError, match="could not parse"):
        load_config(tmp_path)


def test_wrong_type(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.python-sdlc]\npaths = "src"\n')
    with pytest.raises(ConfigError, match="paths must be a list of strings"):
        load_config(tmp_path)


def test_table_not_a_table(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool]\npython-sdlc = "nope"\n')
    with pytest.raises(ConfigError, match="must be a table"):
        load_config(tmp_path)
