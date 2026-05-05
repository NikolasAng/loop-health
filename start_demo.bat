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

echo ⏳ Waiting for Flask server to start (15 seconds)...
set "count=0"
:flask_wait
set /a count+=1
timeout /t 1 /nobreak >nul
if %count% lss 15 (
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5000/health' -TimeoutSec 1 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
    if errorlevel 1 (
        goto flask_wait
    )
)
echo ✅ Flask server ready

echo.
echo 🌐 Starting HTTP server (port 8000)...
echo    - Serving interactive demo
echo.
cd ..
start "HTTP Server - Chess Demo" python -m http.server 8000

echo ⏳ Waiting for HTTP server to start (10 seconds)...
set "count=0"
:http_wait
set /a count+=1
timeout /t 1 /nobreak >nul
if %count% lss 10 (
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/' -TimeoutSec 1 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
    if errorlevel 1 (
        goto http_wait
    )
)
echo ✅ HTTP server ready

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
