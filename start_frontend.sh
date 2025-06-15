#!/bin/bash
echo "🚀 Starting Enhanced Frontend Server..."
echo "======================================"

cd frontend

echo "📱 Modern Frontend Features:"
echo "   • Glass-morphism Design"
echo "   • Tabbed Interface (Guidance + Search)"
echo "   • Quick Question Buttons"
echo "   • Responsive Mobile Design"
echo "   • Real-time Search with Similarity Scores"
echo ""
echo "🌐 Frontend will be available at http://localhost:5000"
echo "🔌 Connecting to MCP server on localhost:8052"
echo ""

# Check if MCP server is running
if curl -s http://localhost:8052 >/dev/null 2>&1; then
    echo "✅ MCP Server is running"
else
    echo "⚠️  MCP Server not detected on port 8052"
    echo "   Start it first with: ./start_mcp_server.sh"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to start MCP server first..."
fi

echo "Press Ctrl+C to stop the frontend"
echo ""

python3 app.py
