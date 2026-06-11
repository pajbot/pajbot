#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if ! command -v uv >/dev/null; then
    echo "We now require uv for dependency management."
    echo "See https://docs.astral.sh/uv/getting-started/installation/ for installation instructions."
    echo "If you really don't want to do this, you can just run pip install . in the repositories main directory."
    exit 1
fi

if [ "$SKIP_PYENV" = "1" ]; then
    echo "If you want to skip the packaged version, call uv sync --no-managed-python"
    exit 1
fi

if [ ! -d scripts ]; then
    echo "This script needs to be called from the root folder, i.e. ./scripts/venvinstall.sh"
    exit 1
fi

INSTALL_DEV="0"

while :; do
    case $1 in
        --dev)
            # Install dev dependencies
            INSTALL_DEV="1"
            ;;

        -?*)
            >&2 printf 'WARN: Unknown option (ignored): %s\n' "$1"
            ;;

        *)
            break
    esac

    shift
done

if [ "$INSTALL_DEV" = "1" ]; then
    echo "Installing requirements + dev requirements from requirements-dev.txt"
    uv sync --extra-dev
else
    echo "Installing requirements requirements from requirements.txt"
    uv sync
fi
