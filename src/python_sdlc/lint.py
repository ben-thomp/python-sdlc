"""Run black, ruff, mypy and pytest as one lint pass."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from python_sdlc.config import LintConfig

PYTEST_NO_TESTS_COLLECTED = 5


class Status(Enum):
    """Outcome of a single lint step."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Step:
    """One tool invocation.

    Attributes:
        name: Heading shown in the output and summary.
        module: Importable module run as ``python -m <module>``.
        args: Arguments placed before the targets.
        targets: Paths appended to the command. Empty means pass none.
        needs_targets: Skip the step when no target exists on disk.
    """

    name: str
    module: str
    args: tuple[str, ...]
    targets: tuple[str, ...] = ()
    needs_targets: bool = True


@dataclass(frozen=True)
class Result:
    """A step together with how it went."""

    step: Step
    status: Status
    detail: str = ""


def build_steps(config: LintConfig, *, fix: bool, run_tests: bool) -> list[Step]:
    """Return the steps to run, in order.

    Check mode runs ``black --check``, ``ruff check``, mypy and pytest. Fix mode
    swaps the first two for ``ruff check --fix`` followed by ``black`` so that
    black has the final say on formatting.
    """
    paths = tuple(config.paths)
    if fix:
        steps = [
            Step("Ruff (fix)", "ruff", ("check", "--fix"), paths),
            Step("Black (format)", "black", (), paths),
        ]
    else:
        steps = [
            Step("Black (check)", "black", ("--check",), paths),
            Step("Ruff (check)", "ruff", ("check",), paths),
        ]
    steps.append(Step("Mypy (types)", "mypy", (), tuple(config.mypy_paths)))
    if run_tests:
        steps.append(
            Step(
                "Pytest (tests)",
                "pytest",
                (),
                tuple(config.test_paths),
                needs_targets=bool(config.test_paths),
            )
        )
    return steps


def _tool_installed(module: str) -> bool:
    """Return whether ``module`` can be imported by this interpreter."""
    return importlib.util.find_spec(module) is not None


def run_step(step: Step, base: Path | None = None) -> Result:
    """Run one step with the current interpreter and classify the outcome."""
    if not _tool_installed(step.module):
        return Result(
            step,
            Status.SKIPPED,
            f"{step.module} is not installed; " "run: pip install 'python-sdlc[lint]'",
        )

    root = base or Path.cwd()
    targets = [t for t in step.targets if (root / t).exists()]
    missing = [t for t in step.targets if t not in targets]
    if step.needs_targets and not targets:
        return Result(step, Status.SKIPPED, f"no such path: {', '.join(missing)}")

    command = [sys.executable, "-m", step.module, *step.args, *targets]
    if missing:
        print(f"note: skipping missing path(s): {', '.join(missing)}", flush=True)
    completed = subprocess.run(command, check=False)

    if completed.returncode == 0:
        return Result(step, Status.PASSED)
    if step.module == "pytest" and completed.returncode == PYTEST_NO_TESTS_COLLECTED:
        return Result(step, Status.SKIPPED, "no tests collected")
    return Result(step, Status.FAILED, f"exit code {completed.returncode}")


def run_lint(
    config: LintConfig,
    *,
    fix: bool = False,
    run_tests: bool = True,
    base: Path | None = None,
) -> int:
    """Run every step, print a summary and return the process exit code.

    Every step runs even if an earlier one fails. Skipped steps are not failures.

    Returns:
        1 if any step failed, otherwise 0.
    """
    results: list[Result] = []
    for step in build_steps(config, fix=fix, run_tests=run_tests):
        print(f"\n{'=' * 60}\n{step.name}\n{'=' * 60}")
        result = run_step(step, base)
        if result.status is Status.SKIPPED:
            print(f"skipped: {result.detail}")
        results.append(result)

    print(f"\n{'=' * 60}\nSummary\n{'=' * 60}")
    for result in results:
        suffix = f" ({result.detail})" if result.detail else ""
        print(f"{result.step.name}: {result.status.value}{suffix}")

    failed = [r for r in results if r.status is Status.FAILED]
    if failed:
        print(f"\nFailed: {', '.join(r.step.name for r in failed)}")
        return 1
    print("\nAll checks passed.")
    return 0
