#!/usr/bin/env bash

set -euo pipefail

# usage: $0 [--check]
# if no --check is specified, files are reformatted
# if --check is specified, no files will be changed, and the script will exit with a non-zero exit code
# if any file does not match the code style.

if ! command -v flake8 >/dev/null; then
  >&2 echo "$0: The flake8 command line tool is not available. (tip: try ./scripts/venvinstall.sh --dev, then source venv/bin/activate)"
  exit 1
fi

if ! command -v npx >/dev/null; then
  >&2 echo "$0: The npx command line tool is not available. (tip: try installing Node.js and npm)"
  exit 1
fi

ISORT_OPTIONS=()

if [ "${1-}" = "--check" ]; then
  RUFF_OPTIONS=""
  PRETTIER_OPTIONS="--check"
  ISORT_OPTIONS+=("--check")
else
  RUFF_OPTIONS="--fix"
  PRETTIER_OPTIONS="--write"
fi

# reformat/check every python file, except venv
>&2 echo " * Running ruff"

uv run ruff check $RUFF_OPTIONS

if [ "${1-}" != "--check" ]; then
    uv run ruff format
fi

# reformat markdown, js, css
>&2 echo " * Running prettier"
npx prettier@^1.18.2 $PRETTIER_OPTIONS '**/*.md' '**/*.js' '**/*.css'

# Run mypy static typing checker
>&2 echo " * Running type checker"
# TODO: re-enable at some point
# uv run pyright .
