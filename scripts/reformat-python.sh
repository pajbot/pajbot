#!/bin/sh

set -e

# usage: $0 [--check]
# if no --check is specified, files are reformatted
# if --check is specified, no files will be changed, and the script will exit with a non-zero exit code
# if any file does not match the code style.

if ! command -v black >/dev/null; then
  >&2 echo "$0: The black command line tool is not available. (tip: try ./scripts/venvinstall.sh --dev, then source venv/bin/activate)"
  exit 1
fi

if [ "$1" = "--check" ]; then
  BLACK_OPTIONS="--check --diff"
else
  BLACK_OPTIONS=""
fi

# reformat/check every python file, except venv
black $BLACK_OPTIONS . --exclude=venv
