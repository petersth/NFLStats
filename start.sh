#!/bin/bash

echo "========================================"
echo "NFL Statistics App"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    if [ ! -x "venv/bin/python" ] || ! venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
        echo "Python upgrade detected. Rebuilding the virtual environment safely..."
        ./install.sh
        if [ $? -ne 0 ]; then
            echo "Installation failed. Please check the error messages above."
            exit 1
        fi
    fi
fi

if [ ! -d "venv" ]; then
    echo "First time setup detected!"
    echo "Running installation..."
    ./install.sh
    if [ $? -ne 0 ]; then
        echo "Installation failed. Please check the error messages above."
        exit 1
    fi
fi

# Check if activation script exists
if [ ! -f "venv/bin/activate" ]; then
    echo "ERROR: Virtual environment activation script not found!"
    echo "Please run ./install.sh to set up the environment."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Skip email prompt
export STREAMLIT_TELEMETRY_OPTOUT=1

# Non-mutating Git update check if Git exists
if command -v git &> /dev/null; then
    echo "Checking for updates..."
    git fetch origin &> /dev/null
    if [ $? -eq 0 ]; then
        BEHIND=$(git rev-list HEAD..origin/main --count 2>/dev/null || echo "0")
        if [ "$BEHIND" -gt "0" ] 2>/dev/null; then
            echo "$BEHIND update(s) available. Run ./update.sh when you are ready to install them."
            echo ""
        else
            echo "You're running the latest version."
            echo ""
        fi
    else
        echo "Could not check for updates - no internet connection or not a Git repository."
        echo ""
    fi
else
    echo "Git not installed - skipping update check."
    echo ""
fi

# Keep the virtual environment synchronized after source updates.
if python -m pip show nfl-data-py &> /dev/null; then
    echo "Removing obsolete nfl-data-py dependency..."
    python -m pip uninstall -y nfl-data-py
fi

if ! python -c "import hashlib, pathlib, sys; requirements = pathlib.Path('requirements.txt'); saved = pathlib.Path('.requirements.hash'); current = hashlib.sha256(requirements.read_bytes()).hexdigest(); sys.exit(0 if saved.exists() and saved.read_text().strip() == current else 1)"; then
    echo "Dependency changes detected. Updating packages..."
    python -m pip install --upgrade -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to update dependencies."
        exit 1
    fi
    python -c "import hashlib, pathlib; requirements = pathlib.Path('requirements.txt'); pathlib.Path('.requirements.hash').write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())"
    echo "Dependencies updated successfully!"
    echo ""
fi

echo "Starting app..."
echo "The app will open in your browser at http://localhost:8501"
echo ""
echo "To stop the app, press Ctrl+C in this window"
echo ""

# Run the Streamlit application
python -m streamlit run app.py

echo ""
echo "App closed with exit code: $?"
