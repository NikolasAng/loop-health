@echo off
REM Wrapper to run servers in the correct directory
cd /d "%~dp0"
if "%1"=="flask" python chess_lh_server.py
if "%1"=="http" python -m http.server 8000
