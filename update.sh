#!/bin/bash

echo "========================================"
echo "NFL Statistics App - Update"
echo "========================================"
echo ""

# Check for git
echo "Checking for git..."
if ! command -v git &> /dev/null; then
    echo "ERROR: Git is not installed"
    echo "Please install Git from https://git-scm.com/downloads"
    exit 1
fi

echo "Git found!"
echo ""

echo "Pulling latest changes from GitHub..."
git pull --ff-only

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to pull updates"
    echo "This might happen if:"
    echo "- You have local changes that conflict"
    echo "- You're not connected to the internet"
    echo "- The repository URL has changed"
    echo ""
    echo "Try running: git status"
    echo "to see what's happening"
    exit 1
fi

echo ""
echo "Checking for dependency updates..."

# Rebuild environments created under the app's former Python support range.
if [ -d "venv" ]; then
    if [ ! -x "venv/bin/python" ] || ! venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
        echo "Python upgrade detected. Rebuilding the virtual environment safely..."
        ./install.sh
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to rebuild the virtual environment."
            exit 1
        fi
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running install.sh..."
    ./install.sh
    if [ $? -ne 0 ]; then
        echo "ERROR: Installation failed. Update did not complete."
        exit 1
    fi
else
    echo "Activating virtual environment..."
    source venv/bin/activate

    if python -m pip show nfl-data-py &> /dev/null; then
        echo "Removing obsolete nfl-data-py dependency..."
        python -m pip uninstall -y nfl-data-py
    fi
    
    echo "Updating dependencies..."
    python -m pip install -r requirements.txt --upgrade
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Dependency update failed. The environment may be partially updated."
        echo "Run ./install.sh after resolving the error before starting the app."
        exit 1
    else
        python -c "import hashlib, pathlib; requirements = pathlib.Path('requirements.txt'); pathlib.Path('.requirements.hash').write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())"
    fi
fi

echo ""
echo "========================================"
echo "Update Complete!"
echo "========================================"
echo ""
echo "To start the app, run: ./start.sh"
echo ""
