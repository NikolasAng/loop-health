# Loop Health - Chess Interactive Demo Launcher (PowerShell)
# More reliable than batch file start commands

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$chessDir = Join-Path $scriptDir "games\chess"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗"
Write-Host "║  Loop Health - Chess Interactive Demo Launcher             ║"
Write-Host "║  Starting Python servers and opening browser...             ║"
Write-Host "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion"
} catch {
    Write-Host "❌ ERROR: Python not found"
    Write-Host "Download from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check packages
Write-Host "Checking required packages..."
try {
    python -c "import flask, chess" 2>&1 | Out-Null
    Write-Host "✓ Required packages found"
} catch {
    Write-Host "⚠️  Installing required packages..."
    pip install flask flask-cors python-chess numpy 2>&1 | Out-Null
    Write-Host "✓ Packages installed"
}

Write-Host ""
Write-Host "🚀 Starting Flask backend server (port 5000)..."
Write-Host "   - Computing real Loop Health metrics"
Write-Host ""

# Start Flask server in chess directory
$flaskJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    python chess_lh_server.py
} -ArgumentList $chessDir -Name "Flask-LH"

Write-Host "⏳ Waiting 12 seconds for Flask server to initialize..."
Start-Sleep -Seconds 12

Write-Host ""
Write-Host "🌐 Starting HTTP server (port 8000)..."
Write-Host "   - Serving from games\chess directory"
Write-Host ""

# Start HTTP server in chess directory
$httpJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    python -m http.server 8000
} -ArgumentList $chessDir -Name "HTTP-Chess"

Write-Host "⏳ Waiting 8 seconds for HTTP server to initialize..."
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "🎮 Opening Chess demo in browser..."
Start-Process "http://localhost:8000/chess_lh_demo.html"

Write-Host ""
Write-Host "✅ ALL SYSTEMS READY!"
Write-Host ""
Write-Host "Servers running in background (PIDs: Flask=$($flaskJob.Id) HTTP=$($httpJob.Id))"
Write-Host ""
Write-Host "Press Ctrl+C to stop servers"
Write-Host ""

# Keep script running
while ($true) {
    if (-not (Get-Job -Id $flaskJob.Id -ErrorAction SilentlyContinue)) {
        Write-Host "⚠️  Flask server stopped"
        break
    }
    if (-not (Get-Job -Id $httpJob.Id -ErrorAction SilentlyContinue)) {
        Write-Host "⚠️  HTTP server stopped"
        break
    }
    Start-Sleep -Seconds 1
}

# Cleanup
Stop-Job -Id $flaskJob.Id -ErrorAction SilentlyContinue
Stop-Job -Id $httpJob.Id -ErrorAction SilentlyContinue
Remove-Job -Id $flaskJob.Id -ErrorAction SilentlyContinue
Remove-Job -Id $httpJob.Id -ErrorAction SilentlyContinue
