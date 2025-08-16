#!/bin/bash

echo "========================================"
echo "NFL Statistics App"
echo "========================================"
echo ""

# Check if virtual environment exists
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
mkdir -p ~/.streamlit
cat > ~/.streamlit/credentials.toml << EOF
[general]
email = ""
EOF

# Simple Git update check if Git exists
if command -v git &> /dev/null; then
    echo "Checking for updates..."
    git fetch origin &> /dev/null
    if [ $? -eq 0 ]; then
        BEHIND=$(git rev-list HEAD...origin/main --count 2>/dev/null || echo "0")
        if [ "$BEHIND" -gt "0" ] 2>/dev/null; then
            echo "Updates available! Pulling latest changes..."
            # Reset any local changes to avoid conflicts
            git reset --hard HEAD
            git pull
            echo "Updates installed successfully!"
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

echo "Starting app..."
echo "The app will open in your browser at http://localhost:8501"
echo ""
echo "To stop the app, press Ctrl+C in this window"
echo ""

# Run the Streamlit application
python -m streamlit run app.py

echo ""
echo "App closed with exit code: $?"