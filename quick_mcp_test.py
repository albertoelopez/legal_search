#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse

# Test MCP server connection
def test_mcp():
    session_id = "9d8dc0685bb64866ab284fcfd8498b41"  # Use the session ID we got earlier
    url = f"http://localhost:8051/messages/?session_id={session_id}"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_available_sources",
            "arguments": {}
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            result = response.read().decode('utf-8')
            print(f"Status: {response.status}")
            print(f"Response: {result}")
            return result
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("Testing MCP server connection...")
    test_mcp() 