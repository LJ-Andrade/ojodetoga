@echo off
title 0J0 de T0GA - Web Interface
echo.
echo Starting 0J0 de T0GA...
echo.

REM Check virtual environment
if not exist "venv" (
    echo Virtual environment not found!
    echo Run: setup.bat
    pause
    exit /b 1
)

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
set IP=%IP: =%

echo Web interface will be available at:
echo    Local:   http://localhost:8080
echo    Network: http://%IP%:8080
echo.
echo Press Ctrl+C to stop
echo.

REM Change to src directory and start the server
cd src
..\venv\Scripts\python.exe web_server.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Server stopped with an error
    pause
)
