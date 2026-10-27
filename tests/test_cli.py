"""Tests for python_sdlc.cli and package entry points."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import python_sdlc
from python_sdlc import cli
from python_sdlc.config import LintConfig


def test_package_importable() -> None:
    assert isinstance(python_sdlc.__version__, str)


def test_lint_defaults_to_check_only(monkeypatch: pytest.MonkeyPatch) -> None:
    run = MagicMock(return_value=0)
    monkeypatch.setattr(cli, "run_lint", run)
    monkeypatch.setattr(cli, "load_config", lambda: LintConfig())
    assert cli.main(["lint"]) == 0
    run.assert_called_once_with(LintConfig(), fix=False, run_tests=True)


def test_lint_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    run = MagicMock(return_value=1)
    monkeypatch.setattr(cli, "run_lint", run)
    monkeypatch.setattr(cli, "load_config", lambda: LintConfig())
    assert cli.main(["lint", "--fix", "--no-tests"]) == 1
    run.assert_called_once_with(LintConfig(), fix=True, run_tests=False)


def test_malformed_config_exits_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.python-sdlc\n")
    monkeypatch.chdir(tmp_path)
    run = MagicMock()
    monkeypatch.setattr(cli, "run_lint", run)
    assert cli.main(["lint"]) == 2
    assert "config error" in capsys.readouterr().err
    run.assert_not_called()


def test_subcommand_required() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2
