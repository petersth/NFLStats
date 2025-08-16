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
git pull

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

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running install.sh..."
    ./install.sh
else
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    echo "Updating dependencies..."
    pip install -r requirements.txt --upgrade
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "WARNING: Some dependencies may not have updated properly"
        echo "The app should still work with existing packages"
    fi
fi

echo ""
echo "========================================"
echo "Update Complete!"
echo "========================================"
echo ""
echo "To start the app, run: ./start.sh"
echo ""