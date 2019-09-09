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

# Install requirements.txt
./venv/bin/pip install -r requirements.txt

# Install dev dependencies
if [ "$1" = "--dev" ]; then
    ./venv/bin/pip install -r requirements-dev.txt
fi
