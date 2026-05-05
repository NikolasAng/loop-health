@echo off
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

echo ⏳ Waiting for Flask server to initialize...
timeout /t 3 /nobreak

echo.
echo 🌐 Starting HTTP server (port 8000)...
echo    - Serving interactive demo
echo.
start "HTTP Server - Chess Demo" python -m http.server 8000

echo ⏳ Waiting for HTTP server to initialize...
timeout /t 2 /nobreak

echo.
echo 🎮 Opening Chess demo in browser...
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
