@echo off
echo ========================================
echo NFL Statistics App - Installation
echo ========================================
echo.

echo Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python found: %PYTHON_VERSION%

REM Check Python version using Python itself
python -c "import sys; exit(0 if sys.version_info.major == 3 else 1)" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python 3 is required
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check minimum version (3.12)
python -c "import sys; exit(0 if sys.version_info.minor >= 12 else 1)" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python 3.12 or higher is required
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python version OK!
echo.

REM Preserve virtual environments created with an older supported Python.
REM They cannot be upgraded in place because a venv is bound to its interpreter.
if exist venv (
    venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Existing virtual environment is not compatible with Python 3.12+.
        python -c "from datetime import datetime; from pathlib import Path; source = Path('venv'); target = source.with_name(f'venv.incompatible.{datetime.now():%%Y%%m%%d%%H%%M%%S%%f}'); source.rename(target); print(f'Preserved the old environment as {target}')"
        if errorlevel 1 (
            echo ERROR: Could not preserve the incompatible virtual environment.
            pause
            exit /b 1
        )
    )
)

echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping creation...
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
)
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing required packages...
echo This may take a few minutes...
echo.

python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Installation failed
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

python -c "import hashlib, pathlib; requirements = pathlib.Path('requirements.txt'); pathlib.Path('.requirements.hash').write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To start the app, double-click "start.bat"
echo.
echo Note: The app uses a virtual environment to avoid
echo conflicts with other Python projects on your system.
echo.
pause
