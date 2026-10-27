# python-sdlc

Python SDLC toolkit.

## Install

```bash
pip install "python-sdlc[lint]"
```

The `lint` extra installs black, ruff, mypy and pytest. Python 3.11 or newer is
required.

## Usage

```bash
sdlc lint             # check only: black --check, ruff check, mypy, pytest
sdlc lint --fix       # ruff check --fix and black, then mypy and pytest
sdlc lint --no-tests  # skip pytest
python -m python_sdlc lint
```

Every step runs even if an earlier one fails. A summary lists each step as
passed, failed or skipped, and the exit code is 1 if any step failed (2 for a bad
configuration). A step is skipped, with a message, when its tool is not installed
or its paths do not exist. Pytest finding no tests is also a skip.

Tools run as `python -m <tool>` using the interpreter that launched `sdlc`, so the
active virtualenv's tools are used.

### Configuration

Optional, in `pyproject.toml`. Defaults are shown.

```toml
[tool.python-sdlc]
paths = ["src", "tests"]  # black and ruff
mypy_paths = ["src"]      # mypy
test_paths = []           # pytest; empty uses your own pytest configuration
```

## Pre-commit hook

Save as `.git/hooks/pre-commit` (and make it executable on macOS/Linux):

```sh
#!/bin/sh
.venv/bin/python -m python_sdlc lint
```

On Windows, Git runs hooks under its bundled `sh`, so use the venv's interpreter:

```sh
#!/bin/sh
.venv/Scripts/python.exe -m python_sdlc lint
```

Calling the venv's Python directly avoids a hook picking up the wrong
interpreter. The hook checks your working tree, not just the staged content, and
check-only mode never modifies files. Add `--no-tests` if pytest is too slow for
a commit hook.
