@echo off
echo ========================================
echo NFL Statistics App - Update
echo ========================================
echo.

echo Checking for git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from https://git-scm.com/downloads
    pause
    exit /b 1
)

echo Git found!
echo.

echo Pulling latest changes from GitHub...
git pull

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to pull updates
    echo This might happen if:
    echo - You have local changes that conflict
    echo - You're not connected to the internet
    echo - The repository URL has changed
    echo.
    echo Try running: git status
    echo to see what's happening
    pause
    exit /b 1
)

echo.
echo Checking for dependency updates...

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Running install.bat...
    call install.bat
) else (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    
    echo Updating dependencies...
    pip install -r requirements.txt --upgrade
    
    if %errorlevel% neq 0 (
        echo.
        echo WARNING: Some dependencies may not have updated properly
        echo The app should still work with existing packages
    )
)

echo.
echo ========================================
echo Update Complete!
echo ========================================
echo.
echo To start the app, double-click "start.bat"
echo.
pause