#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if [ ! -d install ]; then
    >&2 echo "$0: This script needs to be called from the root folder, i.e. ./install/venvinstall"
    exit 1
fi

if [ ! -d venv ]; then
    # Create virtual environment
    echo "Creating python venv"
    python3 -m venv venv
fi

# Upgrade pip
./venv/bin/pip install pip --upgrade

# Install wheel (missing on debian python installations, for example)
./venv/bin/pip install wheel

# Install production dependencies
./venv/bin/pip install -r requirements.txt

# Install dev dependencies
if [ "$1" = "--dev" ]; then
    ./venv/bin/pip install -r requirements-dev.txt
fi
