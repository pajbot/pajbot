#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if [ ! -d install ]; then
    echo "This script needs to be called from the root folder, i.e. ./install/venvinstall.sh"
    exit 1
fi

# Create virtual environment
python3 -m venv venv

# Upgrade pip
./venv/bin/pip install pip --upgrade

# Install requirements.txt
./venv/bin/pip install -r requirements.txt

if [ $CIRCLECI ]; then
    # Install dev deps inside CircleCI
    ./venv/bin/pip install flake8 pytest
fi

if [ $1 = "--dev" ]; then
    # Install dev deps
    ./venv/bin/pip install -r requirements-dev.txt
fi
