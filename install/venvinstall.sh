#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if [ ! -d install ]; then
    echo "This script needs to be called from the root folder, i.e. ./install/venvinstall.sh"
    exit 1
fi

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
. ./venv/bin/activate

extra_install_args=""

if [ -n "$CI" ]; then
    extra_install_args="--progress-bar off"
fi

# Upgrade pip
pip install $extra_install_args pip --upgrade

# Install requirements.txt
pip install $extra_install_args -r requirements.txt
