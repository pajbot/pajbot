#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if [ ! -d scripts ]; then
    echo "This script needs to be called from the root folder, i.e. ./scripts/venvinstall.sh"
    exit 1
fi

if [ ! -d venv ]; then
    # Create virtual environment
    echo "Creating python venv"
    python3 -m venv venv
fi

# Upgrade pip
./venv/bin/pip install pip --upgrade

# Install wheel (see https://stackoverflow.com/q/53204916/4464702)
./venv/bin/pip install wheel

# Install requirements.txt
./venv/bin/pip install -r requirements.txt

while :; do
    case $1 in
        --dev)
            # Install dev dependencies
            ./venv/bin/pip install -r requirements-dev.txt
            ;;

        --nvim)
            # Install NVIM-specific dev dependencies
            ./venv/bin/pip install pynvim jedi
            ;;

        -?*)
            >&2 printf 'WARN: Unknown option (ignored): %s\n' "$1"
            ;;

        *)
            break
    esac

    shift
done
