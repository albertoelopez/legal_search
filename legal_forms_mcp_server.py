#!/usr/bin/env python3
"""
California Legal Forms MCP Server

A simple MCP server that provides search functionality for California legal forms
using our working vector database and embeddings.
"""

import json
import os
from typing import List, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from sentence_transformers import SentenceTransformer
from supabase import create_client

class LegalFormsMCPServer:
    def __init__(self):
        print("🏛️  Initializing California Legal Forms MCP Server")
        
        print("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded!")
        
        self.init_supabase()
        
        self.tools = [
            {
                "name": "search_legal_forms",
                "description": "Search California legal forms using semantic similarity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for legal forms"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    
    def init_supabase(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Supabase connected!")
    
    def create_query_embedding(self, query: str) -> List[float]:
        try:
            embedding = self.embedding_model.encode([query], convert_to_tensor=False)
            return embedding[0].tolist()
        except Exception as e:
            print(f"❌ Error creating embedding for '{query}': {e}")
            return [0.0] * 384
    
    def search_legal_forms(self, query: str, limit: int = 5) -> Dict[str, Any]:
        try:
            query_embedding = self.create_query_embedding(query)
            
            result = self.supabase_client.rpc(
                'match_crawled_pages',
                {
                    'query_embedding': query_embedding,
                    'match_count': limit,
                    'filter': {},
                    'source_filter': 'california_courts_comprehensive'
                }
            ).execute()
            
            if result.data:
                formatted_results = []
                for item in result.data:
                    metadata = item.get('metadata', {})
                    formatted_results.append({
                        'form_code': metadata.get('form_code', 'Unknown'),
                        'title': metadata.get('title', 'Unknown'),
                        'topic': metadata.get('topic', 'Unknown'),
                        'url': item.get('url', ''),
                        'similarity': item.get('similarity', 0),
                        'effective_date': metadata.get('effective_date', ''),
                        'languages': metadata.get('languages', []),
                        'mandatory': metadata.get('mandatory', False)
                    })
                
                return {
                    "success": True,
                    "results": formatted_results,
                    "total_found": len(formatted_results),
                    "query": query
                }
            else:
                return {
                    "success": True,
                    "results": [],
                    "total_found": 0,
                    "query": query,
                    "message": "No forms found matching your query"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def handle_tools_list(self) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": self.tools
            }
        }
    
    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "search_legal_forms":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 5)
            result = self.search_legal_forms(query, limit)
            
            if result["success"]:
                content = f"Found {result['total_found']} legal forms for query: '{query}'\n\n"
                
                for i, form in enumerate(result["results"], 1):
                    content += f"{i}. **{form['form_code']}** - {form['title']}\n"
                    content += f"   📋 Topic: {form['topic']}\n"
                    content += f"   📊 Similarity: {form['similarity']:.3f}\n"
                    content += f"   🔗 URL: {form['url']}\n"
                    if form['effective_date']:
                        content += f"   📅 Effective: {form['effective_date']}\n"
                    if form['languages']:
                        content += f"   🌐 Languages: {', '.join(form['languages'])}\n"
                    content += "\n"
                
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [{"type": "text", "text": content}],
                        "isError": False
                    }
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [{"type": "text", "text": f"Error searching forms: {result['error']}"}],
                        "isError": True
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

class MCPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, mcp_server, *args, **kwargs):
        self.mcp_server = mcp_server
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            if request_data.get("jsonrpc") == "2.0":
                method = request_data.get("method")
                params = request_data.get("params", {})
                request_id = request_data.get("id")
                
                if method == "tools/list":
                    response = self.mcp_server.handle_tools_list()
                    response["id"] = request_id
                elif method == "tools/call":
                    response = self.mcp_server.handle_tools_call(params)
                    response["id"] = request_id
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                self.send_error(400, "Invalid JSON-RPC request")
                
        except Exception as e:
            print(f"❌ Error handling request: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

def create_handler(mcp_server):
    def handler(*args, **kwargs):
        return MCPRequestHandler(mcp_server, *args, **kwargs)
    return handler

def main():
    try:
        mcp_server = LegalFormsMCPServer()
        
        port = int(os.getenv("MCP_PORT", "8052"))
        server = HTTPServer(('localhost', port), create_handler(mcp_server))
        
        print(f"🚀 California Legal Forms MCP Server starting on http://localhost:{port}")
        print("📋 Available tools:")
        for tool in mcp_server.tools:
            print(f"   - {tool['name']}: {tool['description']}")
        print("\n✅ Server ready! Press Ctrl+C to stop.")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    main() 