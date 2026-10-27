"""Command-line interface for python-sdlc."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from python_sdlc import __version__
from python_sdlc.config import ConfigError, load_config
from python_sdlc.lint import run_lint

CONFIG_ERROR_EXIT = 2


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(prog="sdlc", description="Python SDLC toolkit.")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint = subparsers.add_parser(
        "lint",
        help="run black, ruff, mypy and pytest",
        description=(
            "Check-only by default (black --check, ruff check, mypy, pytest). "
            "Settings come from [tool.python-sdlc] in pyproject.toml."
        ),
    )
    lint.add_argument(
        "--fix",
        action="store_true",
        help="run ruff --fix and black instead of the check-only steps",
    )
    lint.add_argument("--no-tests", action="store_true", help="skip pytest")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = build_parser().parse_args(argv)
    if args.command == "lint":
        try:
            config = load_config()
        except ConfigError as exc:
            print(f"sdlc: config error: {exc}", file=sys.stderr)
            return CONFIG_ERROR_EXIT
        return run_lint(config, fix=args.fix, run_tests=not args.no_tests)
    return 0  # pragma: no cover - argparse enforces a known command
