@echo off
setlocal enabledelayedexpansion
REM Loop Health - Chess Interactive Demo Launcher
REM One-click setup for Windows users

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║  Loop Health - Chess Interactive Demo Launcher             ║
echo ║  Starting Python servers and opening browser...             ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python not found. Please install Python 3.8+
    echo.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import flask, chess" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Installing required packages...
    echo    (flask, flask-cors, python-chess, numpy)
    echo.
    pip install flask flask-cors python-chess numpy
    echo.
)

echo 🚀 Starting Flask backend server (port 5000)...
echo    - Computing real Loop Health metrics
echo.
cd games\chess
start "Flask Server - Loop Health Chess LH" python chess_lh_server.py

echo ⏳ Waiting for Flask server to respond (checking every 1 second, timeout 30 seconds)...
set "flask_ready=0"
for /L %%i in (1,1,30) do (
    if !flask_ready! equ 0 (
        timeout /t 1 /nobreak >nul
        python -c "import requests; r=requests.get('http://localhost:5000/health', timeout=1); exit(0 if r.status_code==200 else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            echo ✅ Flask server is ready
            set "flask_ready=1"
        ) else (
            if %%i equ 30 echo ❌ Flask server failed to start after 30 seconds
        )
    )
)

echo.
echo 🌐 Starting HTTP server (port 8000)...
echo    - Serving interactive demo
echo.
cd ..
start "HTTP Server - Chess Demo" python -m http.server 8000

echo ⏳ Waiting for HTTP server to respond (checking every 1 second, timeout 30 seconds)...
set "http_ready=0"
for /L %%i in (1,1,30) do (
    if !http_ready! equ 0 (
        timeout /t 1 /nobreak >nul
        python -c "import requests; r=requests.get('http://localhost:8000/', timeout=1); exit(0 if r.status_code==200 else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            echo ✅ HTTP server is ready
            set "http_ready=1"
        ) else (
            if %%i equ 30 echo ❌ HTTP server failed to start after 30 seconds
        )
    )
)

echo.
echo 🎮 Opening Chess demo in browser...
timeout /t 2 /nobreak
start http://localhost:8000/chess_lh_demo.html

echo.
echo ✅ ALL SYSTEMS READY!
echo.
echo 📊 Access:
echo    ✓ Flask (LH backend):  http://localhost:5000
echo    ✓ Chess demo:          http://localhost:8000/chess_lh_demo.html
echo.
echo 📝 To stop servers: Close the terminal windows
echo.
echo 🔗 GitHub: https://github.com/NikolasAng/loop-health
echo.
pause
