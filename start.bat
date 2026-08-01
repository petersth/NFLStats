@echo off
echo ========================================
echo NFL Statistics App
echo ========================================
echo.

REM Check if virtual environment exists
if exist venv (
    venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Python upgrade detected. Rebuilding the virtual environment safely...
        call install.bat
        if errorlevel 1 (
            echo Installation failed. Please check the error messages above.
            pause
            exit /b 1
        )
    )
)

if not exist venv (
    echo First time setup detected!
    echo Running installation...
    call install.bat
    if errorlevel 1 (
        echo Installation failed. Please check the error messages above.
        pause
        exit /b 1
    )
)

REM Check if activation script exists
if not exist venv\Scripts\activate.bat (
    echo ERROR: Virtual environment activation script not found!
    echo Please run install.bat to set up the environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Skip email prompt
set STREAMLIT_TELEMETRY_OPTOUT=1

REM Non-mutating Git update check if Git exists
git --version >nul 2>&1
if not errorlevel 1 (
    echo Checking for updates...
    git fetch origin >nul 2>&1
    if not errorlevel 1 (
        for /f %%i in ('git rev-list HEAD..origin/main --count 2^>nul') do set BEHIND=%%i
        if defined BEHIND (
            if "%BEHIND%" GTR "0" (
                echo %BEHIND% update(s) available. Run update.bat when you are ready to install them.
                echo.
            ) else (
                echo You're running the latest version.
                echo.
            )
        ) else (
            echo You're running the latest version.
            echo.
        )
    ) else (
        echo Could not check for updates - no internet connection or not a Git repository.
        echo.
    )
) else (
    echo Git not installed - skipping update check.
    echo.
)

REM Keep the virtual environment synchronized after source updates
python -m pip show nfl-data-py >nul 2>&1
if not errorlevel 1 (
    echo Removing obsolete nfl-data-py dependency...
    python -m pip uninstall -y nfl-data-py
)

python -c "import hashlib, pathlib, sys; requirements = pathlib.Path('requirements.txt'); saved = pathlib.Path('.requirements.hash'); current = hashlib.sha256(requirements.read_bytes()).hexdigest(); sys.exit(0 if saved.exists() and saved.read_text().strip() == current else 1)"
if errorlevel 1 (
    echo Dependency changes detected. Updating packages...
    python -m pip install --upgrade -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to update dependencies.
        pause
        exit /b 1
    )
    python -c "import hashlib, pathlib; requirements = pathlib.Path('requirements.txt'); pathlib.Path('.requirements.hash').write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())"
    echo Dependencies updated successfully!
    echo.
)

echo Starting app...
echo The app will open in your browser at http://localhost:8501
echo.
echo To stop the app, press Ctrl+C in this window
echo.

REM Run the Streamlit application
python -m streamlit run app.py

echo.
echo App closed with exit code: %errorlevel%
pause
