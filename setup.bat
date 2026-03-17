@echo off
title 0J0 de T0GA - Setup
echo.
echo Setting up 0J0 de T0GA...
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        echo Make sure Python is installed and in your PATH
        pause
        exit /b 1
    )
)

echo Using virtual environment...

REM Upgrade pip
echo Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
venv\Scripts\pip.exe install -r requirements.txt

echo.
echo Setup complete!
echo.
echo To run the web interface:
echo   start.bat
echo.
pause
