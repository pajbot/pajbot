#!/usr/bin/env bash

set -euo pipefail

# usage: $0 [--check]
# if no --check is specified, files are reformatted
# if --check is specified, no files will be changed, and the script will exit with a non-zero exit code
# if any file does not match the code style.

if ! command -v black >/dev/null; then
  >&2 echo "$0: The black command line tool is not available. (tip: try ./scripts/venvinstall.sh --dev, then source venv/bin/activate)"
  exit 1
fi

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
  BLACK_OPTIONS="--check --diff"
  PRETTIER_OPTIONS="--check"
  ISORT_OPTIONS+=("--check")
else
  BLACK_OPTIONS=""
  PRETTIER_OPTIONS="--write"
fi

# reformat/check every python file, except venv
black $BLACK_OPTIONS . --exclude=venv

# reformat markdown, js, css
npx prettier@^1.18.2 $PRETTIER_OPTIONS '**/*.md' '**/*.js' '**/*.css'

# Run linter
flake8

# Run mypy static typing checker
mypy pajbot

# Sort imports
isort pajbot "${ISORT_OPTIONS[@]}"
