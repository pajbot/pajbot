#!/usr/bin/env bash

set -euo pipefail

# export PYTEST_ADDOPTS="-W error::DeprecationWarning"
export PYTEST_ADDOPTS="-W default::DeprecationWarning"

if ! command -v uv >/dev/null; then
    echo "This script requires uv installed. You can manually run tests with pytest in your venv."
    exit 1
fi

if [ ! -d scripts ]; then
    echo "This script needs to be called from the root folder, i.e. ./scripts/venvinstall.sh"
    exit 1
fi

uv run pytest pajbot
