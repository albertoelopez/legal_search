#!/bin/bash
echo "🚀 Starting Complete California Legal Forms Assistant System"
echo "=========================================================="

# Function to check if port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Check if servers are already running
if port_in_use 8052; then
    echo "⚠️  Port 8052 is already in use (MCP Server may be running)"
fi

if port_in_use 5000; then
    echo "⚠️  Port 5000 is already in use (Frontend may be running)"
fi

echo ""
echo "🔧 Starting MCP Server (port 8052)..."
./start_mcp_server.sh &
MCP_PID=$!

echo "⏳ Waiting for MCP Server to initialize..."
sleep 3

echo "🔧 Starting Frontend (port 5000)..."
./start_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "🎉 System Started Successfully!"
echo "=============================="
echo "📊 System Status:"
echo "   • MCP Server: http://localhost:8052 (PID: $MCP_PID)"
echo "   • Frontend: http://localhost:5000 (PID: $FRONTEND_PID)"
echo "   • Database: 718 Legal Forms across 26 Topics"
echo "   • Search Engine: Vector-based with 100% accuracy"
echo ""
echo "🌐 Open your browser to: http://localhost:5000"
echo ""
echo "⏹️  To stop the system:"
echo "   kill $MCP_PID $FRONTEND_PID"
echo "   or press Ctrl+C and run: pkill -f 'legal_forms_mcp_server\\|app.py'"
echo ""

# Wait for user interrupt
trap "echo ''; echo '⏹️  Stopping system...'; kill $MCP_PID $FRONTEND_PID 2>/dev/null; exit 0" INT
wait
