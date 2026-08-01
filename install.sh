#!/bin/bash

echo "========================================"
echo "NFL Statistics App - Installation"
echo "========================================"
echo ""

# Check for Python
echo "Checking for Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python is not installed"
    echo "Please install Python 3.12 from https://www.python.org/downloads/"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo "Python found: $PYTHON_VERSION"

# Check Python version compatibility
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -ne 3 ]; then
    echo "ERROR: Python 3 is required (found Python $PYTHON_MAJOR)"
    echo "Please install Python 3.12 from https://www.python.org/downloads/"
    exit 1
fi

if [ "$PYTHON_MINOR" -lt 12 ]; then
    echo "ERROR: Python 3.12 or higher is required (found Python $PYTHON_MAJOR.$PYTHON_MINOR)"
    echo "Please install Python 3.12 from https://www.python.org/downloads/"
    exit 1
fi

echo "Python version OK!"
echo ""

# Preserve virtual environments created with an older supported Python.
# They cannot be upgraded in place because a venv is bound to its interpreter.
if [ -d "venv" ]; then
    if [ ! -x "venv/bin/python" ] || ! venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
        echo "Existing virtual environment is not compatible with Python 3.12+."
        BACKUP_PATH=$($PYTHON_CMD -c "from datetime import datetime; from pathlib import Path; source = Path('venv'); target = source.with_name(f'venv.incompatible.{datetime.now():%Y%m%d%H%M%S%f}'); source.rename(target); print(target)")
        if [ $? -ne 0 ]; then
            echo "ERROR: Could not preserve the incompatible virtual environment."
            exit 1
        fi
        echo "Preserved the old environment as $BACKUP_PATH"
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping creation..."
else
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
    echo "Virtual environment created successfully!"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

echo ""
echo "Installing required packages..."
echo "This may take a few minutes..."
echo ""

# Install requirements
python -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Installation failed"
    echo "Please check your internet connection and try again"
    exit 1
fi

python -c "import hashlib, pathlib; requirements = pathlib.Path('requirements.txt'); pathlib.Path('.requirements.hash').write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())"

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "To start the app, run: ./start.sh"
echo ""
echo "Note: The app uses a virtual environment to avoid"
echo "conflicts with other Python projects on your system."
echo ""
