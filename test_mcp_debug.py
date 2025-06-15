import requests
import json

SESSION_ID = "20e2f90f1c4f4155a4438f0863dbe162"
MESSAGES_URL = f"http://localhost:8051/messages/?session_id={SESSION_ID}"

def call_mcp_tool_debug(tool_name, arguments, tool_id=1):
    """Call an MCP tool and show debug info."""
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
    
    print(f"Sending to: {MESSAGES_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(MESSAGES_URL, data=json.dumps(payload), headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Raw Response: {response.text}")
        
        if response.text.strip():
            try:
                return response.json()
            except json.JSONDecodeError as e:
                return {"error": f"JSON decode error: {e}", "raw_response": response.text}
        else:
            return {"error": "Empty response"}
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    result = call_mcp_tool_debug("get_available_sources", {})
    print(f"\nFinal result: {json.dumps(result, indent=2)}") 