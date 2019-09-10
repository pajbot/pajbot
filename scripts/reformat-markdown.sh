#!/bin/sh

set -e

# usage: $0 [--check]
# if no --check is specified, files are reformatted
# if --check is specified, no files will be changed, and the script will exit with a non-zero exit code
# if any file does not match the code style.

if ! command -v npx >/dev/null; then
  >&2 echo "$0: The npx command line tool is not available. (tip: try installing Node.js and npm)"
  exit 1
fi

if [ "$1" = "--check" ]; then
  PRETTIER_OPTIONS="--check"
else
  PRETTIER_OPTIONS="--write"
fi

npx prettier@^1.18.2 $PRETTIER_OPTIONS '**/*.md'
