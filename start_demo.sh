#!/bin/bash
# Loop Health - Chess Interactive Demo Launcher
# One-click setup for Linux/Mac users

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Loop Health - Chess Interactive Demo Launcher             ║"
echo "║  Starting Python servers and opening browser...             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python not found. Please install Python 3.8+"
    echo ""
    echo "On macOS: brew install python3"
    echo "On Ubuntu/Debian: sudo apt-get install python3"
    exit 1
fi

# Check if required packages are installed
python3 -c "import flask, chess" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing required packages..."
    echo "   (flask, flask-cors, python-chess, numpy)"
    echo ""
    pip3 install flask flask-cors python-chess numpy
    echo ""
fi

echo "🚀 Starting Flask backend server (port 5000)..."
echo "   - Computing real Loop Health metrics"
echo ""
cd games/chess
python3 chess_lh_server.py &
FLASK_PID=$!

echo "⏳ Waiting 12 seconds for Flask server to initialize..."
sleep 12

echo ""
echo "🌐 Starting HTTP server (port 8000)..."
echo "   - Serving interactive demo from games/chess directory"
echo ""
python3 -m http.server 8000 >/dev/null 2>&1 &
HTTP_PID=$!

echo "⏳ Waiting 8 seconds for HTTP server to initialize..."
sleep 8

echo ""
echo "🎮 Opening Chess demo in browser..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8000/chess_lh_demo.html
else
    xdg-open http://localhost:8000/chess_lh_demo.html 2>/dev/null || echo "Please open http://localhost:8000/chess_lh_demo.html in your browser"
fi

echo ""
echo "✅ ALL SYSTEMS READY!"
echo ""
echo "📊 Access:"
echo "   ✓ Flask (LH backend):  http://localhost:5000"
echo "   ✓ Chess demo:          http://localhost:8000/chess_lh_demo.html"
echo ""
echo "📝 To stop servers: Press Ctrl+C"
echo ""
echo "🔗 GitHub: https://github.com/NikolasAng/loop-health"
echo ""

# Wait for Ctrl+C
wait
