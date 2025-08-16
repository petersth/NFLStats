@echo off
echo ========================================
echo NFL Statistics App
echo ========================================
echo.

REM Check if virtual environment exists
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
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
echo [general] > "%USERPROFILE%\.streamlit\credentials.toml"
echo email = "" >> "%USERPROFILE%\.streamlit\credentials.toml"

REM Simple Git update check if Git exists
git --version >nul 2>&1
if not errorlevel 1 (
    echo Checking for updates...
    git fetch origin >nul 2>&1
    if not errorlevel 1 (
        for /f %%i in ('git rev-list HEAD...origin/main --count 2^>nul') do set BEHIND=%%i
        if defined BEHIND (
            if "%BEHIND%" GTR "0" (
                echo Updates available! Pulling latest changes...
                REM Reset any local changes to avoid conflicts
                git reset --hard HEAD
                git pull
                echo Updates installed successfully!
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