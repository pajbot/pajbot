#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if [ ! -d install ]; then
    echo "This script needs to be called from the root folder, i.e. ./install/venvinstall.sh"
    exit 1
fi

# Create virtual environment
python3 -m venv myvenv

# Activate virtual environment
. myvenv/bin/activate

# Upgrade pip
pip install pip --upgrade

# Install requirements.txt
pip install -r requirements.txt
