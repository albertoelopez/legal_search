import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from playwright.sync_api import sync_playwright
import urllib.request
import urllib.parse

FORMS_URL = "https://courts.ca.gov/rules-forms/find-your-court-forms"
OUTPUT_JSON = "court_forms.json"
EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"
FAISS_INDEX_PATH = "forms.index"
FORMS_TEXTS_PATH = "forms_texts.json"
LLM_API_URL = "https://api.gmi-serving.com/v1/chat/completions"
LLM_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY2ZjY4ZGNiLTc2MjYtNDU1YS04MTJlLWNjZWQ0NGM1MmFmMSIsInR5cGUiOiJpZV9tb2RlbCJ9.wSR0pMUfjAfTijf8jJSaiec1FutdKCcCJq6RlJo62uM "
MCP_BASE_URL = "http://localhost:8051"

class CourtFormsAgent:
    def __init__(self, forms_url=FORMS_URL, output_json=OUTPUT_JSON, embeddings_model=EMBEDDINGS_MODEL, faiss_index_path=FAISS_INDEX_PATH, forms_texts_path=FORMS_TEXTS_PATH):
        self.forms_url = forms_url
        self.output_json = output_json
        self.embeddings_model = embeddings_model
        self.faiss_index_path = faiss_index_path
        self.forms_texts_path = forms_texts_path
        self.forms = None
        self.model = SentenceTransformer(self.embeddings_model)
        self.index = None
        self.form_texts = None
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

    def mcp_crawl_single_page(self, url=FORMS_URL):
        """Crawl a single page using MCP server."""
        result = self.call_mcp_tool("crawl_single_page", {"url": url})
        print(f"MCP crawl_single_page result: {result}")
        return result

    def mcp_smart_crawl_url(self, url=FORMS_URL, max_depth=3, max_concurrent=10):
        """Smart crawl URL using MCP server."""
        result = self.call_mcp_tool("smart_crawl_url", {
            "url": url,
            "max_depth": max_depth,
            "max_concurrent": max_concurrent
        })
        print(f"MCP smart_crawl_url result: {result}")
        return result

    def mcp_get_available_sources(self):
        """Get available sources from MCP server."""
        result = self.call_mcp_tool("get_available_sources", {})
        print(f"MCP available sources: {result}")
        return result

    def mcp_perform_rag_query(self, query, source=None, match_count=5):
        """Perform RAG query using MCP server."""
        arguments = {"query": query, "match_count": match_count}
        if source:
            arguments["source"] = source
        
        result = self.call_mcp_tool("perform_rag_query", arguments)
        return result

    def mcp_search_code_examples(self, query, source_id=None, match_count=5):
        """Search code examples using MCP server (if agentic RAG is enabled)."""
        arguments = {"query": query, "match_count": match_count}
        if source_id:
            arguments["source_id"] = source_id
        
        result = self.call_mcp_tool("search_code_examples", arguments)
        return result

    def answer_with_mcp_rag(self, user_question, source=None, match_count=5):
        """Answer question using MCP RAG and then LLM."""
        print(f"Querying MCP server for: {user_question}")
        rag_result = self.mcp_perform_rag_query(user_question, source=source, match_count=match_count)
        
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
            "suggest which form(s) are most relevant and what information the user needs to fill out. "
            "For each form you mention, include its full name and the direct URL if available from the provided list.\n"
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

    def crawl_forms(self):
        """Crawl the California Courts forms page and extract form titles and URLs."""
        forms = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.forms_url)
            page.wait_for_load_state("networkidle")
            links = page.query_selector_all("a[href*='forms/']")
            for link in links:
                title = link.inner_text().strip()
                url = link.get_attribute("href")
                if url and title:
                    if not url.startswith("http"):
                        url = "https://courts.ca.gov" + url
                    forms.append({"title": title, "url": url})
            browser.close()
        with open(self.output_json, "w") as f:
            json.dump(forms, f, indent=2)
        print(f"Extracted {len(forms)} forms and saved to {self.output_json}")
        self.forms = forms
        return forms

    def load_forms(self):
        with open(self.output_json, "r") as f:
            self.forms = json.load(f)
        return self.forms

    def build_index(self):
        """Build FAISS index from forms using local embeddings."""
        if self.forms is None:
            self.load_forms()
        form_texts = [f"{form['title']}: {form['url']}" for form in self.forms]
        embeddings = self.model.encode(form_texts, show_progress_bar=True)
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(np.array(embeddings).astype("float32"))
        faiss.write_index(index, self.faiss_index_path)
        with open(self.forms_texts_path, "w") as f:
            json.dump(form_texts, f)
        print(f"Built FAISS index and saved to {self.faiss_index_path}")
        self.index = index
        self.form_texts = form_texts

    def load_index(self):
        """Load FAISS index and form texts from disk."""
        self.index = faiss.read_index(self.faiss_index_path)
        with open(self.forms_texts_path) as f:
            self.form_texts = json.load(f)
        if self.forms is None:
            self.load_forms()

    def retrieve_forms(self, query, top_k=5):
        """Semantic search for relevant forms using local embeddings and FAISS."""
        if self.index is None or self.form_texts is None:
            self.load_index()
        query_emb = self.model.encode([query])
        D, I = self.index.search(np.array(query_emb).astype("float32"), top_k)
        return [self.forms[i] for i in I[0]]

    def answer_question(self, user_question, top_k=5):
        relevant_forms = self.retrieve_forms(user_question, top_k=top_k)
        context = "\n".join(f"- {f['title']}: {f['url']}" for f in relevant_forms)
        prompt = (
            "You are a helpful AI assistant. Given the following court forms and a user question, "
            "suggest which form(s) are most relevant and what information the user needs to fill out. "
            "For each form you mention, include its full name and the direct URL if available from the provided list.\n"
            f"Court Forms:\n{context}\n\nQuestion: {user_question}"
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY.strip()}"
        }
        data = {
            "model": "deepseek-ai/DeepSeek-R1-0528",
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 500
        }
        response = requests.post(LLM_API_URL, headers=headers, json=data)
        response.raise_for_status()
        resp_json = response.json()
        print("Full LLM response:", json.dumps(resp_json, indent=2))
        try:
            msg = resp_json["choices"][0]["message"]
            if msg.get("content"):
                return msg["content"]
            elif msg.get("reasoning_content"):
                return msg["reasoning_content"]
            else:
                return "No valid answer found in LLM response."
        except (KeyError, IndexError):
            return "No valid answer found in LLM response."

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Court Forms Agent (Local + MCP)")
    parser.add_argument("--crawl", action="store_true", help="Crawl and update court forms list (local).")
    parser.add_argument("--build-index", action="store_true", help="Build FAISS index from forms (local).")
    parser.add_argument("--ask", type=str, help="Ask a question about court forms (local semantic search).")
    
    # MCP options
    parser.add_argument("--mcp-crawl-single", action="store_true", help="Use MCP server to crawl single page.")
    parser.add_argument("--mcp-crawl-smart", action="store_true", help="Use MCP server to smart crawl the forms site.")
    parser.add_argument("--mcp-sources", action="store_true", help="Get available sources from MCP server.")
    parser.add_argument("--mcp-ask", type=str, help="Ask a question using MCP server RAG.")
    parser.add_argument("--mcp-code", type=str, help="Search for code examples using MCP server.")
    
    args = parser.parse_args()

    agent = CourtFormsAgent()
    
    # Local operations
    if args.crawl:
        agent.crawl_forms()
    if args.build_index:
        agent.build_index()
    if args.ask:
        answer = agent.answer_question(args.ask)
        print("\nLocal LLM Answer:\n", answer)
    
    # MCP operations
    if args.mcp_crawl_single:
        agent.mcp_crawl_single_page()
    if args.mcp_crawl_smart:
        agent.mcp_smart_crawl_url()
    if args.mcp_sources:
        agent.mcp_get_available_sources()
    if args.mcp_ask:
        answer = agent.answer_with_mcp_rag(args.mcp_ask)
        print("\nMCP RAG Answer:\n", answer)
    if args.mcp_code:
        result = agent.mcp_search_code_examples(args.mcp_code)
        print("\nMCP Code Examples:\n", result) 