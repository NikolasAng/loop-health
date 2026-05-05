@echo off
REM Loop Health - Chess Interactive Demo Launcher
REM Launches the PowerShell version for reliability

cd /d "%~dp0"

REM Execute PowerShell script with proper execution policy
powershell -NoProfile -ExecutionPolicy Bypass -File "%cd%\start_demo.ps1"

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
