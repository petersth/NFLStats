#!/bin/bash

echo "========================================"
echo "NFL Statistics App - Setup"
echo "========================================"
echo ""

# Check if we're already in the Stats app directory
if [ -f "app.py" ] && [ -f "requirements.txt" ]; then
    echo "Detected existing NFL Statistics App files."
    
    # Check if .git exists
    if [ -d ".git" ]; then
        echo "Git repository already configured!"
        echo ""
        echo "You can now run ./start.sh to launch the app."
        exit 0
    fi
    
    echo ""
    echo "This appears to be a ZIP download without Git history."
    echo "To enable automatic updates, this needs to be converted to a Git repository."
    echo ""
    
    # Check for git
    if ! command -v git &> /dev/null; then
        echo "Git is not installed."
        echo ""
        echo "To enable automatic updates, please:"
        echo "1. Install Git from: https://git-scm.com/downloads"
        echo "2. Run this setup script again"
        echo ""
        echo "Or you can continue without updates by running ./start.sh"
        exit 1
    fi
    
    echo "Convert to Git repository for automatic updates? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Skipping Git setup. You can run ./start.sh but won't get automatic updates."
        exit 0
    fi
    
    echo ""
    echo "Initializing Git repository..."
    
    # Initialize git repo
    git init
    
    # Add the remote
    git remote add origin https://github.com/petersth/NFLStats.git
    
    # Disable credential helper for public repo
    git config --local credential.helper ""
    
    # Fetch all remote branches
    echo "Fetching from remote repository..."
    git fetch origin
    
    # Reset to match remote main branch exactly
    echo "Synchronizing with remote repository..."
    git reset --hard origin/main
    
    # Set up branch tracking
    git branch --set-upstream-to=origin/main main
    
    # Make sure we're on main branch
    git checkout main 2>/dev/null || git checkout -b main
    
    echo ""
    echo "Git repository configured! Automatic updates are now enabled."
    echo "You can now run ./start.sh to launch the app."
    exit 0
fi

# If we're not in the app directory, do a fresh clone
echo "Checking for Git..."
if ! command -v git &> /dev/null; then
    echo "Git is not installed."
    echo ""
    echo "Please install Git from: https://git-scm.com/downloads"
    echo "Then run this script again."
    echo ""
    echo "Why Git is needed:"
    echo "- Enables automatic updates"
    echo "- Ensures you always have the latest features"
    exit 1
fi

echo "Git found! Downloading the application..."
echo ""

# Clone the repository (disable credential helper for public repo)
git -c credential.helper= clone https://github.com/petersth/NFLStats.git Stats
if [ $? -ne 0 ]; then
    echo "Failed to download the application."
    echo "Please check your internet connection and try again."
    exit 1
fi

echo ""
echo "========================================"
echo "Download Complete!"
echo "========================================"
echo ""
echo "The app has been downloaded to the 'Stats' folder."
echo ""
echo "Next steps:"
echo "1. Open the Stats folder"
echo "2. Run ./start.sh to launch the app"
echo ""