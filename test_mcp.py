import requests
import json
import sseclient

MCP_SSE_URL = "http://localhost:8051/sse"

class MCPTester:
    def __init__(self):
        self.mcp_session_id = None

    def get_mcp_session_id(self):
        """Get session ID from MCP server SSE endpoint."""
        if self.mcp_session_id:
            return self.mcp_session_id
        
        response = requests.get(MCP_SSE_URL, stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.event == "endpoint":
                # Extract session_id from the data
                self.mcp_session_id = event.data.split("session_id=")[-1]
                break
        
        return self.mcp_session_id

    def call_mcp_tool(self, tool_name, arguments, tool_id=1):
        """Call an MCP tool using JSON-RPC 2.0 format."""
        session_id = self.get_mcp_session_id()
        if not session_id:
            return {"error": "Could not get MCP session ID"}
        
        messages_url = f"http://localhost:8051/messages/?session_id={session_id}"
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
            response = requests.post(messages_url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def test_get_sources(self):
        """Test getting available sources."""
        result = self.call_mcp_tool("get_available_sources", {})
        print(f"Available sources: {json.dumps(result, indent=2)}")
        return result

    def test_crawl_single_page(self, url="https://courts.ca.gov/rules-forms/find-your-court-forms"):
        """Test crawling a single page."""
        result = self.call_mcp_tool("crawl_single_page", {"url": url})
        print(f"Crawl result: {json.dumps(result, indent=2)}")
        return result

    def test_rag_query(self, query="What forms do I need for divorce?"):
        """Test RAG query."""
        result = self.call_mcp_tool("perform_rag_query", {"query": query, "match_count": 3})
        print(f"RAG result: {json.dumps(result, indent=2)}")
        return result

if __name__ == "__main__":
    import sys
    
    tester = MCPTester()
    
    if len(sys.argv) < 2:
        print("Usage: python test_mcp.py [sources|crawl|rag]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "sources":
        tester.test_get_sources()
    elif command == "crawl":
        tester.test_crawl_single_page()
    elif command == "rag":
        query = sys.argv[2] if len(sys.argv) > 2 else "What forms do I need for divorce?"
        tester.test_rag_query(query)
    else:
        print("Unknown command. Use: sources, crawl, or rag") 