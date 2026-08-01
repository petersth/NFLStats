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
git pull --ff-only

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

REM Rebuild environments created under the app's former Python support range.
if exist venv (
    venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Python upgrade detected. Rebuilding the virtual environment safely...
        call install.bat
        if errorlevel 1 (
            echo ERROR: Failed to rebuild the virtual environment.
            exit /b 1
        )
    )
)

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Running install.bat...
    call install.bat
) else (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat

    python -m pip show nfl-data-py >nul 2>&1
    if not errorlevel 1 (
        echo Removing obsolete nfl-data-py dependency...
        python -m pip uninstall -y nfl-data-py
    )
    
    echo Updating dependencies...
    python -m pip install -r requirements.txt --upgrade
    
    if errorlevel 1 (
        echo.
        echo ERROR: Dependency update failed. The environment may be partially updated.
        echo Run install.bat after resolving the error before starting the app.
        exit /b 1
    ) else (
        python -c "import hashlib, pathlib; requirements = pathlib.Path('requirements.txt'); pathlib.Path('.requirements.hash').write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())"
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
