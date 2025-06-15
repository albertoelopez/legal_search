#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse

MCP_BASE_URL = "http://localhost:8051"
LLM_API_URL = "https://api.gmi-serving.com/v1/chat/completions"
LLM_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY2ZjY4ZGNiLTc2MjYtNDU1YS04MTJlLWNjZWQ0NGM1MmFmMSIsInR5cGUiOiJpZV9tb2RlbCJ9.wSR0pMUfjAfTijf8jJSaiec1FutdKCcCJq6RlJo62uM "

class MCPAgent:
    def __init__(self):
        self.mcp_session_id = None

    def get_mcp_session_id(self):
        """Get session ID from MCP server SSE endpoint."""
        if self.mcp_session_id:
            return self.mcp_session_id
        
        try:
            with urllib.request.urlopen(f"{MCP_BASE_URL}/sse") as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: /messages/?session_id='):
                        self.mcp_session_id = line.split('session_id=')[1]
                        break
        except Exception as e:
            print(f"Error getting session ID: {e}")
            # Fallback to a default session ID for testing
            self.mcp_session_id = "test-session-123"
        
        return self.mcp_session_id

    def call_mcp_tool(self, tool_name, arguments, tool_id=1):
        """Call an MCP tool using JSON-RPC 2.0 format."""
        session_id = self.get_mcp_session_id()
        if not session_id:
            return {"error": "Could not get MCP session ID"}
        
        url = f"{MCP_BASE_URL}/messages/?session_id={session_id}"
        payload = {
            "jsonrpc": "2.0",
            "id": tool_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req) as response:
                result = response.read().decode('utf-8')
                if result.strip() == "Accepted":
                    return {"status": "accepted", "message": "Request submitted to MCP server"}
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {"status": "accepted", "raw_response": result}
        except Exception as e:
            return {"error": str(e)}

    def test_mcp_sources(self):
        """Test getting available sources."""
        result = self.call_mcp_tool("get_available_sources", {})
        print(f"Available sources: {json.dumps(result, indent=2)}")
        return result

    def test_mcp_crawl(self, url="https://courts.ca.gov/rules-forms/find-your-court-forms"):
        """Test crawling the court forms page."""
        result = self.call_mcp_tool("crawl_single_page", {"url": url})
        print(f"Crawl result: {json.dumps(result, indent=2)}")
        return result

    def test_mcp_rag(self, query="What forms do I need for divorce?"):
        """Test RAG query."""
        result = self.call_mcp_tool("perform_rag_query", {"query": query, "match_count": 3})
        print(f"RAG result: {json.dumps(result, indent=2)}")
        return result

    def answer_with_mcp_rag(self, user_question):
        """Answer question using MCP RAG and then LLM."""
        print(f"Querying MCP server for: {user_question}")
        rag_result = self.test_mcp_rag(user_question)
        
        # Handle MCP response
        if "status" in rag_result and rag_result["status"] == "accepted":
            context = f"MCP server accepted the query: {user_question}. The server is processing the request asynchronously."
        elif "result" in rag_result and "content" in rag_result["result"]:
            context = rag_result["result"]["content"]
        elif "error" in rag_result:
            return f"Error from MCP server: {rag_result['error']}"
        else:
            context = str(rag_result)
        
        # Send context + question to LLM
        prompt = (
            "You are a helpful AI assistant. Given the following retrieved legal content and a user question, "
            "suggest which form(s) are most relevant and what information the user needs to fill out.\n"
            f"Retrieved Content:\n{context}\n\nQuestion: {user_question}"
        )
        
        data = json.dumps({
            "model": "deepseek-ai/DeepSeek-R1-0528",
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 500
        }).encode('utf-8')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY.strip()}"
        }
        
        try:
            req = urllib.request.Request(LLM_API_URL, data=data, headers=headers)
            with urllib.request.urlopen(req) as response:
                resp_json = json.loads(response.read().decode('utf-8'))
                
            msg = resp_json["choices"][0]["message"]
            if msg.get("content"):
                return msg["content"]
            elif msg.get("reasoning_content"):
                return msg["reasoning_content"]
            else:
                return "No valid answer found in LLM response."
        except Exception as e:
            return f"Error calling LLM: {e}"

if __name__ == "__main__":
    import sys
    
    agent = MCPAgent()
    
    if len(sys.argv) < 2:
        print("Usage: python3 mcp_only_test.py [sources|crawl|rag|ask] [question]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "sources":
        agent.test_mcp_sources()
    elif command == "crawl":
        agent.test_mcp_crawl()
    elif command == "rag":
        query = sys.argv[2] if len(sys.argv) > 2 else "What forms do I need for divorce?"
        agent.test_mcp_rag(query)
    elif command == "ask":
        question = sys.argv[2] if len(sys.argv) > 2 else "What forms do I need for divorce?"
        answer = agent.answer_with_mcp_rag(question)
        print(f"\nFinal Answer:\n{answer}")
    else:
        print("Unknown command. Use: sources, crawl, rag, or ask") 