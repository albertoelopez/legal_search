#!/bin/bash
echo "🧪 Testing Enhanced California Legal Forms Assistant"
echo "=================================================="

echo "1. Testing Vector Search..."
if [ -f "test_vector_search.py" ]; then
    python3 test_vector_search.py
else
    echo "⚠️  test_vector_search.py not found"
fi

echo ""
echo "2. Testing MCP Server..."
if [ -f "test_mcp_search.py" ]; then
    python3 test_mcp_search.py
else
    echo "⚠️  test_mcp_search.py not found"
fi

echo ""
echo "3. System Status Summary:"
echo "   • Vector Search: $([ -f "test_vector_search.py" ] && echo "✅ Available" || echo "❌ Missing")"
echo "   • MCP Server: $([ -f "legal_forms_mcp_server.py" ] && echo "✅ Available" || echo "❌ Missing")"
echo "   • Frontend: $([ -f "frontend/app.py" ] && echo "✅ Available" || echo "❌ Missing")"
echo "   • Database: $([ ! -z "$SUPABASE_URL" ] && echo "✅ Configured" || echo "⚠️  Not Configured")"
