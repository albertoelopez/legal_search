#!/usr/bin/env python3
import json
import os
import urllib.request
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MCP_BASE_URL = os.getenv('MCP_BASE_URL', 'http://localhost:8051')
LLM_API_URL = os.getenv('LLM_API_URL', 'https://api.gmi-serving.com/v1/chat/completions')
LLM_API_KEY = os.getenv('LLM_API_KEY')

if not LLM_API_KEY:
    print("⚠️  Warning: LLM_API_KEY not set in environment variables. LLM features will be disabled.")

class LegalAgent:
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
            self.mcp_session_id = "fallback-session-123"
        
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

    def crawl_court_forms(self):
        """Crawl the California court forms page."""
        print("🔍 Crawling California court forms...")
        result = self.call_mcp_tool("crawl_single_page", {
            "url": "https://courts.ca.gov/rules-forms/find-your-court-forms"
        })
        
        if "status" in result and result["status"] == "accepted":
            print("✅ Crawling request submitted successfully!")
            print("📄 The MCP server is now crawling and indexing court forms...")
            return True
        else:
            print(f"❌ Crawling failed: {result}")
            return False

    def smart_crawl_court_forms(self):
        """Smart crawl the court forms with depth control."""
        print("🔍 Smart crawling California court forms (with depth)...")
        result = self.call_mcp_tool("smart_crawl_url", {
            "url": "https://courts.ca.gov/rules-forms/find-your-court-forms",
            "max_depth": 2,
            "max_concurrent": 5
        })
        
        if "status" in result and result["status"] == "accepted":
            print("✅ Smart crawling request submitted successfully!")
            print("📄 The MCP server is crawling multiple pages and building a comprehensive index...")
            return True
        else:
            print(f"❌ Smart crawling failed: {result}")
            return False

    def get_available_sources(self):
        """Get available data sources from MCP server."""
        print("📊 Checking available data sources...")
        result = self.call_mcp_tool("get_available_sources", {})
        
        if "status" in result and result["status"] == "accepted":
            print("✅ Data sources request submitted!")
            return result
        else:
            print(f"Available sources: {json.dumps(result, indent=2)}")
            return result

    def search_forms(self, query):
        """Search for forms using MCP RAG."""
        print(f"🔎 Searching for: '{query}'")
        result = self.call_mcp_tool("perform_rag_query", {
            "query": query,
            "match_count": 5
        })
        
        if "status" in result and result["status"] == "accepted":
            print("✅ Search request submitted to MCP server!")
            print("🤖 The server is searching through crawled court forms...")
            return result
        elif "result" in result:
            print("📋 Found relevant forms:")
            return result
        else:
            print(f"Search result: {json.dumps(result, indent=2)}")
            return result

    def provide_legal_guidance(self, question):
        """Provide legal guidance based on the question."""
        print(f"\n💼 Legal Question: {question}")
        print("=" * 60)
        
        # Search for relevant forms
        search_result = self.search_forms(question)
        
        # Provide guidance based on question type
        guidance = self.get_guidance_for_question(question)
        
        print("\n📋 Legal Guidance:")
        print(guidance)
        
        print("\n🔗 Recommended Actions:")
        if "divorce" in question.lower():
            print("1. Visit: https://courts.ca.gov/selfhelp-divorce")
            print("2. Consider mediation before filing")
            print("3. Gather financial documents")
            print("4. Look for forms FL-100, FL-110, FL-120")
        elif "custody" in question.lower() or "child" in question.lower():
            print("1. Visit: https://courts.ca.gov/selfhelp-custody")
            print("2. Consider child's best interests")
            print("3. Look for forms FL-300, FL-311, FL-341")
        elif "support" in question.lower():
            print("1. Visit: https://courts.ca.gov/selfhelp-support")
            print("2. Gather income documentation")
            print("3. Look for forms FL-150, FL-155")
        else:
            print("1. Visit: https://courts.ca.gov/selfhelp")
            print("2. Consult with a legal professional")
            print("3. Review relevant court forms")
        
        return search_result

    def get_guidance_for_question(self, question):
        """Provide specific guidance based on the question."""
        question_lower = question.lower()
        
        if "divorce" in question_lower:
            return """
For divorce proceedings in California, you typically need:

• Petition for Dissolution (FL-100) - Initial filing
• Summons (FL-110) - Legal notice to spouse  
• Declaration of Disclosure (FL-140/FL-142) - Financial information
• Settlement Agreement (FL-180) - If uncontested

California is a no-fault divorce state, meaning you don't need to prove wrongdoing.
You must meet residency requirements (6 months in CA, 3 months in county).
"""
        
        elif "custody" in question_lower or "child" in question_lower:
            return """
For child custody matters in California:

• Request for Order (FL-300) - To request custody/visitation
• Declaration (FL-311) - Your statement to the court
• Child Custody and Visitation Application (FL-311)
• Parenting Plan (FL-341E) - Detailed custody arrangement

California courts prioritize the child's best interests. Consider factors like:
- Child's health, safety, and welfare
- History of abuse or violence
- Parent's ability to care for the child
"""
        
        elif "support" in question_lower:
            return """
For child or spousal support in California:

• Income and Expense Declaration (FL-150) - Financial information
• Request for Order (FL-300) - To request support
• Child Support Case Registry Form (FL-191)

Support calculations are based on:
- Both parents' income
- Time spent with each parent
- Number of children
- Other factors like health insurance, childcare costs
"""
        
        else:
            return """
For general legal matters in California courts:

1. Identify the correct court (family, civil, criminal, etc.)
2. Determine required forms for your specific situation
3. Gather necessary documentation
4. Consider if you need legal representation
5. Check filing fees and fee waiver options

Visit the California Courts self-help website for specific guidance.
"""

if __name__ == "__main__":
    import sys
    
    agent = LegalAgent()
    
    print("🏛️  California Legal Forms Assistant")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 working_legal_agent.py crawl          # Crawl court forms")
        print("  python3 working_legal_agent.py smart-crawl    # Smart crawl with depth")
        print("  python3 working_legal_agent.py sources        # Check data sources")
        print("  python3 working_legal_agent.py search 'query' # Search forms")
        print("  python3 working_legal_agent.py ask 'question' # Get legal guidance")
        print("\nExamples:")
        print("  python3 working_legal_agent.py ask 'How do I file for divorce?'")
        print("  python3 working_legal_agent.py ask 'What forms for child custody?'")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "crawl":
        agent.crawl_court_forms()
    elif command == "smart-crawl":
        agent.smart_crawl_court_forms()
    elif command == "sources":
        agent.get_available_sources()
    elif command == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else "divorce forms"
        agent.search_forms(query)
    elif command == "ask":
        question = sys.argv[2] if len(sys.argv) > 2 else "What forms do I need for divorce?"
        agent.provide_legal_guidance(question)
    else:
        print(f"Unknown command: {command}")
        print("Use: crawl, smart-crawl, sources, search, or ask") 