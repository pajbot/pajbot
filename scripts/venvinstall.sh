#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if [ ! -d install ]; then
    echo "This script needs to be called from the root folder, i.e. ./scripts/venvinstall.sh"
    exit 1
fi

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
. ./venv/bin/activate

# Upgrade pip
pip install pip --upgrade

# Install wheel (missing on debian, apparently, and useful
# for installation of some packages in requirements.txt)
pip install wheel

# Install requirements.txt
pip install -r requirements.txt
