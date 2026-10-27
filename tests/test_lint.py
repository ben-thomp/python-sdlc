"""Tests for python_sdlc.lint. Subprocess calls are mocked."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from python_sdlc import lint
from python_sdlc.config import LintConfig
from python_sdlc.lint import Status, build_steps, run_lint, run_step


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    return tmp_path


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace subprocess.run; every tool is 'installed' and exits 0."""
    mock = MagicMock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(lint.subprocess, "run", mock)
    monkeypatch.setattr(lint, "_tool_installed", lambda module: True)
    return mock


def commands(mock: MagicMock) -> list[list[str]]:
    return [call.args[0] for call in mock.call_args_list]


def test_default_is_check_only() -> None:
    steps = build_steps(LintConfig(), fix=False, run_tests=True)
    assert [(s.module, s.args) for s in steps] == [
        ("black", ("--check",)),
        ("ruff", ("check",)),
        ("mypy", ()),
        ("pytest", ()),
    ]


def test_fix_runs_ruff_then_black() -> None:
    steps = build_steps(LintConfig(), fix=True, run_tests=True)
    assert [(s.module, s.args) for s in steps[:2]] == [
        ("ruff", ("check", "--fix")),
        ("black", ()),
    ]
    assert [s.module for s in steps[2:]] == ["mypy", "pytest"]


def test_no_tests_drops_pytest() -> None:
    steps = build_steps(LintConfig(), fix=False, run_tests=False)
    assert "pytest" not in [s.module for s in steps]


def test_uses_sys_executable_without_shell(fake_run: MagicMock, project: Path) -> None:
    assert run_lint(LintConfig(), base=project) == 0
    for call in fake_run.call_args_list:
        assert call.args[0][:2] == [sys.executable, "-m"]
        assert not call.kwargs.get("shell")


def test_per_tool_targets(fake_run: MagicMock, project: Path) -> None:
    run_lint(LintConfig(), base=project)
    assert commands(fake_run) == [
        [sys.executable, "-m", "black", "--check", "src", "tests"],
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
        [sys.executable, "-m", "mypy", "src"],
        [sys.executable, "-m", "pytest"],
    ]


def test_test_paths_passed_to_pytest(fake_run: MagicMock, project: Path) -> None:
    run_lint(LintConfig(test_paths=["tests"]), base=project)
    assert commands(fake_run)[-1] == [sys.executable, "-m", "pytest", "tests"]


def test_missing_tool_is_skipped(
    fake_run: MagicMock, monkeypatch: pytest.MonkeyPatch, project: Path
) -> None:
    monkeypatch.setattr(lint, "_tool_installed", lambda module: module != "ruff")
    step = build_steps(LintConfig(), fix=False, run_tests=True)[1]
    result = run_step(step, project)
    assert result.status is Status.SKIPPED
    assert "ruff is not installed" in result.detail
    assert "python-sdlc[lint]" in result.detail
    assert run_lint(LintConfig(), base=project) == 0


def test_missing_path_is_skipped(fake_run: MagicMock, tmp_path: Path) -> None:
    step = build_steps(LintConfig(), fix=False, run_tests=False)[2]  # mypy src
    result = run_step(step, tmp_path)
    assert result.status is Status.SKIPPED
    assert "src" in result.detail
    fake_run.assert_not_called()


def test_some_missing_paths_are_dropped(fake_run: MagicMock, tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()  # no tests/ directory
    run_lint(LintConfig(), base=tmp_path, run_tests=False)
    assert commands(fake_run)[0] == [
        sys.executable,
        "-m",
        "black",
        "--check",
        "src",
    ]


def test_all_steps_run_after_failure(fake_run: MagicMock, project: Path) -> None:
    fake_run.side_effect = [
        subprocess.CompletedProcess([], 1),
        subprocess.CompletedProcess([], 0),
        subprocess.CompletedProcess([], 1),
        subprocess.CompletedProcess([], 0),
    ]
    assert run_lint(LintConfig(), base=project) == 1
    assert fake_run.call_count == 4


def test_summary_names_failures(
    fake_run: MagicMock, project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_run.side_effect = [subprocess.CompletedProcess([], 1)] + [
        subprocess.CompletedProcess([], 0)
    ] * 3
    run_lint(LintConfig(), base=project)
    out = capsys.readouterr().out
    assert "Black (check): failed" in out
    assert "Failed: Black (check)" in out


def test_pytest_exit_5_is_skipped(fake_run: MagicMock, project: Path) -> None:
    fake_run.return_value = subprocess.CompletedProcess([], 5)
    step = build_steps(LintConfig(), fix=False, run_tests=True)[-1]
    assert run_step(step, project).status is Status.SKIPPED


def test_exit_5_from_other_tools_is_failure(fake_run: MagicMock, project: Path) -> None:
    fake_run.return_value = subprocess.CompletedProcess([], 5)
    step = build_steps(LintConfig(), fix=False, run_tests=True)[0]
    assert run_step(step, project).status is Status.FAILED
