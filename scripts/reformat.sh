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
echo "Checking Python formatting with black"
uv run black $BLACK_OPTIONS . --exclude=venv
echo ""

# reformat markdown, js, css
echo "Reformatting markdown/js/css with prettier"
npx --yes prettier@1.19.1 $PRETTIER_OPTIONS '**/*.md' '**/*.js' '**/*.css'
echo ""

# Run linter
echo "Linting with flake8"
uv run flake8 pajbot
echo ""

# Run mypy static typing checker
echo "Type-checking with mypy"
uv run mypy pajbot
echo ""

# Sort imports
echo "Sorting imports with isort"
uv run isort pajbot "${ISORT_OPTIONS[@]}"
echo ""
