@echo off
echo ========================================
echo NFL Statistics App - Setup
echo ========================================
echo.

REM Check if we're already in the Stats app directory
if exist app.py if exist requirements.txt (
    echo Detected existing NFL Statistics App files.
    
    REM Check if .git exists
    if exist .git (
        echo Git repository already configured!
        echo.
        echo You can now run start.bat to launch the app.
        pause
        exit /b 0
    )
    
    echo.
    echo This appears to be a ZIP download without Git history.
    echo To enable automatic updates, this needs to be converted to a Git repository.
    echo.
    
    REM Check for git
    git --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Git is not installed.
        echo.
        echo To enable automatic updates, please:
        echo 1. Install Git from: https://git-scm.com/downloads
        echo 2. Run this setup script again
        echo.
        echo Or you can continue without updates by running start.bat
        pause
        exit /b 1
    )
    
    choice /C YN /M "Convert to Git repository for automatic updates"
    if %errorlevel% equ 2 (
        echo.
        echo Skipping Git setup. You can run start.bat but won't get automatic updates.
        pause
        exit /b 0
    )
    
    echo.
    echo Initializing Git repository...
    
    REM Initialize git repo
    git init
    
    REM Add the remote
    git remote add origin https://github.com/petersth/NFLStats.git
    
    REM Disable credential helper for public repo
    git config --local credential.helper ""
    
    REM Fetch all remote branches
    echo Fetching from remote repository...
    git fetch origin
    
    REM Reset to match remote main branch exactly
    echo Synchronizing with remote repository...
    git reset --hard origin/main
    
    REM Set up branch tracking
    git branch --set-upstream-to=origin/main main
    
    REM Make sure we're on main branch
    git checkout main 2>nul || git checkout -b main
    
    echo.
    echo Git repository configured! Automatic updates are now enabled.
    echo You can now run start.bat to launch the app.
    pause
    exit /b 0
)

REM If we're not in the app directory, do a fresh clone
echo Checking for Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Git is not installed. 
    echo.
    echo Please install Git from: https://git-scm.com/downloads
    echo Then run this script again.
    echo.
    echo Why Git is needed:
    echo - Enables automatic updates
    echo - Ensures you always have the latest features
    pause
    exit /b 1
)

echo Git found! Downloading the application...
echo.

REM Clone the repository (disable credential helper for public repo)
git -c credential.helper= clone https://github.com/petersth/NFLStats.git Stats
if %errorlevel% neq 0 (
    echo Failed to download the application.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Download Complete!
echo ========================================
echo.
echo The app has been downloaded to the 'Stats' folder.
echo.
echo Next steps:
echo 1. Open the Stats folder
echo 2. Double-click start.bat to run the app
echo.
pause