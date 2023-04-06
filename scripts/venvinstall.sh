#!/bin/sh

set -e

# Ensure this script is called from the correct folder
if [ ! -d scripts ]; then
    echo "This script needs to be called from the root folder, i.e. ./scripts/venvinstall.sh"
    exit 1
fi

if [ ! -d venv ]; then
    # Create virtual environment
    if [ "$SKIP_PYENV" = "1" ]; then
        echo "Attempting to create virtual environment using system Python"
        python3 -m venv venv
        printf "Created virtual environment using system Python: "
        python3 --version
    else
        echo "Attempting to create virtual environment using pyenv's Python"
        if ! command -v pyenv >/dev/null; then
            echo "Error: Unable to find pyenv to create the virtual environment with the appropriate Python version."
            echo "You must install pyenv & put the appropriate shell initialization into your .bashrc or .zshrc to be able to use pyenv."
            echo "If you want to use your system Python (and your system Python is high enough version), run this script again with the SKIP_PYENV=1 environment variable set."
            exit 1
        fi
        pyenv exec python3 -m venv venv
        printf "Created virtual environment using pyenv Python: "
        pyenv exec python3 --version
    fi
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
