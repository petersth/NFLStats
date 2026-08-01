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
    echo Git-managed updates require a separately cloned repository.
    echo.
    
    REM Check for git
    git --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Git is not installed.
        echo.
        echo To use Git-managed updates, please:
        echo 1. Install Git from: https://git-scm.com/downloads
        echo 2. Run this setup script again
        echo.
        echo Or you can continue without updates by running start.bat
        pause
        exit /b 1
    )
    
    echo.
    echo This ZIP installation will be left unchanged to protect local files.
    echo To use Git updates, clone a fresh copy in a different directory:
    echo git clone https://github.com/petersth/NFLStats.git
    echo You can continue using this copy with start.bat.
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
    echo - Enables update notifications and explicit update commands
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
