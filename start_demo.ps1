# Loop Health - Chess Interactive Demo Launcher (PowerShell)
# More reliable than batch file start commands

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$chessDir = Join-Path $scriptDir "games\chess"
$logDir = Join-Path $scriptDir "logs"

# Create logs directory
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗"
Write-Host "║  Loop Health - Chess Interactive Demo Launcher             ║"
Write-Host "║  Starting Python servers and opening browser...             ║"
Write-Host "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

# Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Python not found"
    Write-Host "Download from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "✓ Python found: $pythonVersion"

# Check packages
Write-Host "Checking required packages..."
python -c "import flask, chess" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Installing required packages..."
    pip install flask flask-cors python-chess numpy 2>&1 | Out-Null
    Write-Host "✓ Packages installed"
}
else {
    Write-Host "✓ Required packages found"
}

Write-Host ""
Write-Host "🚀 Starting Flask backend server (port 5000)..."
Write-Host "   - Computing real Loop Health metrics"
Write-Host "   - Working directory: $chessDir"
Write-Host ""

# Start Flask server using Start-Process with explicit working directory
$flaskLog = Join-Path $logDir "flask.log"
Start-Process -FilePath python -ArgumentList "chess_lh_server.py" `
    -WorkingDirectory $chessDir `
    -RedirectStandardOutput $flaskLog `
    -RedirectStandardError $flaskLog `
    -WindowStyle Minimized `
    -PassThru | Out-Null

Write-Host "⏳ Waiting 12 seconds for Flask server to initialize..."
for ($i = 1; $i -le 12; $i++) {
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1
}
Write-Host " Done"

# Check if Flask is responding
Write-Host "Checking Flask server..."
$flaskReady = $false
for ($i = 1; $i -le 5; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Flask server responding"
            $flaskReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $flaskReady) {
    Write-Host "⚠️  Flask server may not be ready, but continuing..."
}

Write-Host ""
Write-Host "🌐 Starting HTTP server (port 8000)..."
Write-Host "   - Serving from games\chess directory"
Write-Host ""

# Start HTTP server using Start-Process with explicit working directory
$httpLog = Join-Path $logDir "http.log"
Start-Process -FilePath python -ArgumentList "-m http.server 8000" `
    -WorkingDirectory $chessDir `
    -RedirectStandardOutput $httpLog `
    -RedirectStandardError $httpLog `
    -WindowStyle Minimized `
    -PassThru | Out-Null

Write-Host "⏳ Waiting 8 seconds for HTTP server to initialize..."
for ($i = 1; $i -le 8; $i++) {
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1
}
Write-Host " Done"

# Check if HTTP is responding
Write-Host "Checking HTTP server..."
$httpReady = $false
for ($i = 1; $i -le 5; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ HTTP server responding"
            $httpReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $httpReady) {
    Write-Host "⚠️  HTTP server may not be ready, but continuing..."
}

Write-Host ""
Write-Host "🎮 Opening Chess demo in browser..."
Write-Host ""
Start-Process "http://localhost:8000/chess_lh_demo.html"

Write-Host "✅ ALL SYSTEMS READY!"
Write-Host ""
Write-Host "Servers running in background"
Write-Host "Logs: $logDir"
Write-Host ""
Write-Host "If you see an error in the browser, check:"
Write-Host "  - Flask log: $flaskLog"
Write-Host "  - HTTP log:  $httpLog"
Write-Host ""
