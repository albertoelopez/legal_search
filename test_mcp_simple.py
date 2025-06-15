import requests
import json

# Use the session ID we got from the curl test earlier
SESSION_ID = "9d8dc0685bb64866ab284fcfd8498b41"
MESSAGES_URL = f"http://localhost:8051/messages/?session_id={SESSION_ID}"

def call_mcp_tool(tool_name, arguments, tool_id=1):
    """Call an MCP tool using JSON-RPC 2.0 format."""
    payload = {
        "jsonrpc": "2.0",
        "id": tool_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(MESSAGES_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def test_get_sources():
    """Test getting available sources."""
    result = call_mcp_tool("get_available_sources", {})
    print(f"Available sources: {json.dumps(result, indent=2)}")
    return result

def test_crawl_single_page(url="https://courts.ca.gov/rules-forms/find-your-court-forms"):
    """Test crawling a single page."""
    result = call_mcp_tool("crawl_single_page", {"url": url})
    print(f"Crawl result: {json.dumps(result, indent=2)}")
    return result

def test_rag_query(query="What forms do I need for divorce?"):
    """Test RAG query."""
    result = call_mcp_tool("perform_rag_query", {"query": query, "match_count": 3})
    print(f"RAG result: {json.dumps(result, indent=2)}")
    return result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_mcp_simple.py [sources|crawl|rag]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "sources":
        test_get_sources()
    elif command == "crawl":
        test_crawl_single_page()
    elif command == "rag":
        query = sys.argv[2] if len(sys.argv) > 2 else "What forms do I need for divorce?"
        test_rag_query(query)
    else:
        print("Unknown command. Use: sources, crawl, or rag") 