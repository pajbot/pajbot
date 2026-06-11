#!/usr/bin/env bash

set -euo pipefail

# usage: $0 [--check]
# if no --check is specified, files are reformatted
# if --check is specified, no files will be changed, and the script will exit with a non-zero exit code
# if any file does not match the code style.

MIN_PY_VERSION="py311"
ISORT_OPTIONS=()

if [ "${1-}" = "--check" ]; then
  BLACK_OPTIONS="--target-version $MIN_PY_VERSION --check --diff"
  PRETTIER_OPTIONS="--check"
  ISORT_OPTIONS+=("--check")
else
  BLACK_OPTIONS="--target-version $MIN_PY_VERSION"
  PRETTIER_OPTIONS="--write"
fi

# reformat/check every python file, except venv
uv run black $BLACK_OPTIONS . --exclude=venv

# reformat markdown, js, css
npx prettier@^1.18.2 $PRETTIER_OPTIONS '**/*.md' '**/*.js' '**/*.css'

# Run linter
uv run flake8 pajbot

# Run mypy static typing checker
uv run mypy pajbot

# Sort imports
uv run isort pajbot "${ISORT_OPTIONS[@]}"
