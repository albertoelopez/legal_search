import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from playwright.sync_api import sync_playwright
import urllib.request
import urllib.parse
from supabase import create_client, Client
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FORMS_URL = "https://courts.ca.gov/rules-forms/find-your-court-forms"
OUTPUT_JSON = "court_forms.json"
EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"
LLM_API_URL = os.getenv('LLM_API_URL', 'https://api.gmi-serving.com/v1/chat/completions')
LLM_API_KEY = os.getenv('LLM_API_KEY')
MCP_BASE_URL = os.getenv('MCP_BASE_URL', 'http://localhost:8051')

if not LLM_API_KEY:
    print("⚠️  Warning: LLM_API_KEY not set in environment variables. LLM features will be disabled.")

class CourtFormsAgent:
    def __init__(self, forms_url=FORMS_URL, output_json=OUTPUT_JSON, embeddings_model=EMBEDDINGS_MODEL):
        self.forms_url = forms_url
        self.output_json = output_json
        self.embeddings_model = embeddings_model
        self.forms = None
        self.model = SentenceTransformer(self.embeddings_model)
        self.mcp_session_id = None
        
        # Initialize Supabase client
        self.supabase_client = None
        self.init_supabase()

    def init_supabase(self):
        """Initialize Supabase client for vector database operations."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            print("⚠️  Warning: SUPABASE_URL and SUPABASE_SERVICE_KEY not set. Vector search will be disabled.")
            return
        
        try:
            self.supabase_client = create_client(supabase_url, supabase_key)
            print("✅ Connected to Supabase vector database")
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            self.supabase_client = None

    def create_query_embedding(self, query: str) -> List[float]:
        """Create embedding for a search query."""
        try:
            embedding = self.model.encode([query], convert_to_tensor=False)
            return embedding[0].tolist()
        except Exception as e:
            print(f"❌ Error creating embedding for '{query}': {e}")
            return [0.0] * 384

    def _clean_title_to_english(self, title: str) -> str:
        """Clean form titles to show only English text."""
        if not title:
            return "Unknown Form"
        
        # Remove common non-English text patterns
        import re
        
        # Remove Chinese characters (汉语)
        title = re.sub(r'汉语', '', title)
        
        # Remove Korean characters (한국어)
        title = re.sub(r'한국어', '', title)
        
        # Remove Spanish marker (español)
        title = re.sub(r'español', '', title)
        
        # Remove Vietnamese marker (Tiếng Việt)
        title = re.sub(r'Tiếng Việt', '', title)
        
        # Remove Arabic marker (اَلْعَرَبِيَّةُ)
        title = re.sub(r'اَلْعَرَبِيَّةُ', '', title)
        
        # Remove Tagalog marker
        title = re.sub(r'Tagalog', '', title)
        
        # Remove any remaining non-ASCII characters except common punctuation
        title = re.sub(r'[^\x00-\x7F]+', '', title)
        
        # Clean up extra whitespace and trailing punctuation
        title = re.sub(r'\s+', ' ', title)  # Multiple spaces to single space
        title = title.strip()
        
        # Remove trailing commas or other punctuation that might be left over
        title = re.sub(r'[,\s]+$', '', title)
        
        return title if title else "Unknown Form"

    def search_vector_database(self, query: str, limit: int = 10, similarity_threshold: float = 0.1) -> List[Dict[str, Any]]:
        """Search the vector database for relevant forms."""
        if not self.supabase_client:
            print("❌ Supabase client not initialized. Cannot perform vector search.")
            return []
        
        try:
            # Create embedding for the query
            query_embedding = self.create_query_embedding(query)
            
            # Try the database function first
            result = self.supabase_client.rpc(
                'match_crawled_pages',
                {
                    'query_embedding': query_embedding,
                    'match_count': limit,
                    'filter': {},
                    'source_filter': None
                }
            ).execute()
            
            if result.data:
                # Filter by similarity threshold and format results
                filtered_results = []
                for item in result.data:
                    if item.get('similarity', 0) >= similarity_threshold:
                        metadata = item.get('metadata', {})
                        raw_title = metadata.get('title', 'Unknown Form')
                        clean_title = self._clean_title_to_english(raw_title)
                        filtered_results.append({
                            'title': clean_title,
                            'url': item.get('url', ''),
                            'form_code': metadata.get('form_code', ''),
                            'topic': metadata.get('topic', ''),
                            'content': item.get('content', ''),
                            'similarity': item.get('similarity', 0),
                            'metadata': metadata
                        })
                
                return filtered_results
            else:
                # Fallback: Manual similarity calculation
                print("⚠️  Database function returned 0 results, trying manual calculation...")
                return self._manual_similarity_search(query_embedding, limit, similarity_threshold)
                
        except Exception as e:
            print(f"❌ Error searching vector database for '{query}': {e}")
            # Fallback: Manual similarity calculation
            print("⚠️  Trying manual similarity calculation as fallback...")
            return self._manual_similarity_search(self.create_query_embedding(query), limit, similarity_threshold)

    def _manual_similarity_search(self, query_embedding: List[float], limit: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """Manual similarity search as fallback when database function fails."""
        try:
            import ast
            import numpy as np
            
            # Get all records (or a reasonable subset)
            result = self.supabase_client.table('crawled_pages').select(
                'id, url, content, metadata, embedding'
            ).limit(min(1000, limit * 20)).execute()  # Get more records to search through
            
            if not result.data:
                return []
            
            query_vec = np.array(query_embedding)
            similarities = []
            
            for item in result.data:
                try:
                    # Parse stored embedding
                    embedding_str = item['embedding']
                    stored_embedding = np.array(ast.literal_eval(embedding_str))
                    
                    # Calculate cosine similarity
                    dot_product = np.dot(query_vec, stored_embedding)
                    norm_query = np.linalg.norm(query_vec)
                    norm_stored = np.linalg.norm(stored_embedding)
                    
                    if norm_query > 0 and norm_stored > 0:
                        cosine_sim = dot_product / (norm_query * norm_stored)
                        similarity = cosine_sim  # Use cosine similarity directly
                        
                        if similarity >= similarity_threshold:
                            metadata = item.get('metadata', {})
                            raw_title = metadata.get('title', 'Unknown Form')
                            clean_title = self._clean_title_to_english(raw_title)
                            similarities.append({
                                'title': clean_title,
                                'url': item.get('url', ''),
                                'form_code': metadata.get('form_code', ''),
                                'topic': metadata.get('topic', ''),
                                'content': item.get('content', ''),
                                'similarity': similarity,
                                'metadata': metadata
                            })
                            
                except Exception as e:
                    # Skip records with parsing errors
                    continue
            
            # Sort by similarity (highest first) and return top results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            print(f"❌ Manual similarity search failed: {e}")
            return []

    def search_by_topic(self, topic: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search forms by specific topic using metadata filtering."""
        if not self.supabase_client:
            print("❌ Supabase client not initialized. Cannot perform topic search.")
            return []
        
        try:
            result = self.supabase_client.table('crawled_pages').select(
                'id, content, metadata, url'
            ).contains('metadata', {'topic': topic}).limit(limit).execute()
            
            if result.data:
                formatted_results = []
                for item in result.data:
                    metadata = item.get('metadata', {})
                    raw_title = metadata.get('title', 'Unknown Form')
                    clean_title = self._clean_title_to_english(raw_title)
                    formatted_results.append({
                        'title': clean_title,
                        'url': item.get('url', ''),
                        'form_code': metadata.get('form_code', ''),
                        'topic': metadata.get('topic', ''),
                        'content': item.get('content', ''),
                        'metadata': metadata
                    })
                return formatted_results
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error searching by topic '{topic}': {e}")
            return []

    def get_available_topics(self) -> List[str]:
        """Get list of available topics from the database."""
        if not self.supabase_client:
            return []
        
        try:
            # Get distinct topics from metadata
            result = self.supabase_client.table('crawled_pages').select('metadata').execute()
            
            topics = set()
            if result.data:
                for item in result.data:
                    metadata = item.get('metadata', {})
                    topic = metadata.get('topic')
                    if topic:
                        topics.add(topic)
            
            return sorted(list(topics))
            
        except Exception as e:
            print(f"❌ Error getting available topics: {e}")
            return []

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database."""
        if not self.supabase_client:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Get total count
            result = self.supabase_client.table('crawled_pages').select('id', count='exact').execute()
            total_count = result.count if hasattr(result, 'count') else len(result.data)
            
            # Get topics
            topics = self.get_available_topics()
            
            return {
                "total_forms": total_count,
                "total_topics": len(topics),
                "available_topics": topics,
                "database_ready": True
            }
            
        except Exception as e:
            return {"error": str(e), "database_ready": False}

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

    def answer_question(self, user_question, top_k=5):
        """Answer questions using vector database search and LLM."""
        print(f"🔍 Searching vector database for: {user_question}")
        
        # Search the vector database with a very low threshold to catch any results
        relevant_forms = self.search_vector_database(user_question, limit=top_k, similarity_threshold=0.0)
        
        if not relevant_forms:
            return "❌ No relevant forms found in the database. Please try a different query or check if the database is properly set up."
        
        # Format context for LLM
        context_parts = []
        for form in relevant_forms:
            similarity = form.get('similarity', 0)
            title = form.get('title', 'Unknown')
            form_code = form.get('form_code', '')
            topic = form.get('topic', '')
            url = form.get('url', '')
            
            context_parts.append(f"- {form_code} - {title} (Topic: {topic}, Similarity: {similarity:.3f})")
            if url:
                context_parts.append(f"  URL: {url}")
        
        context = "\n".join(context_parts)
        
        prompt = (
            "You are a helpful AI assistant specializing in California court forms. "
            "Given the following relevant court forms and a user question, "
            "suggest which form(s) are most relevant and provide guidance on what information is needed. "
            "Include the form codes, full names, and URLs when available.\n\n"
            f"Relevant Forms:\n{context}\n\nUser Question: {user_question}\n\n"
            "Please provide a helpful response that includes:\n"
            "1. The most relevant form(s) for their situation\n"
            "2. Brief explanation of what each form is for\n"
            "3. Any important steps or requirements they should know about"
        )
        
        # Call LLM
        data = json.dumps({
            "model": "deepseek-ai/DeepSeek-R1-0528",
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant specializing in California court forms and legal procedures."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 800
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

    # Legacy methods for backward compatibility (now deprecated)
    def crawl_forms(self):
        """Legacy method - crawling is now handled by comprehensive crawler."""
        print("⚠️  This method is deprecated. Use the comprehensive crawler instead.")
        print("   Run: python3 comprehensive_legal_crawler.py")
        return []

    def load_forms(self):
        """Legacy method - forms are now loaded from vector database."""
        print("⚠️  This method is deprecated. Forms are now loaded from the vector database.")
        return []

    def build_index(self):
        """Legacy method - indexing is now handled by the vector database."""
        print("⚠️  This method is deprecated. Vector indexing is handled by Supabase.")
        print("   Forms are automatically indexed when stored in the database.")

    def load_index(self):
        """Legacy method - index is now the vector database."""
        print("⚠️  This method is deprecated. Vector search uses the Supabase database directly.")

    def retrieve_forms(self, query, top_k=5):
        """Retrieve forms using vector database search."""
        return self.search_vector_database(query, limit=top_k)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Court Forms Agent (Vector Database + MCP)")
    
    # Vector database operations
    parser.add_argument("--ask", type=str, help="Ask a question about court forms using vector database search.")
    parser.add_argument("--search", type=str, help="Search for forms using vector similarity.")
    parser.add_argument("--topic", type=str, help="Search forms by specific topic.")
    parser.add_argument("--topics", action="store_true", help="List all available topics.")
    parser.add_argument("--stats", action="store_true", help="Show database statistics.")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return (default: 5).")
    
    # Legacy operations (deprecated)
    parser.add_argument("--crawl", action="store_true", help="[DEPRECATED] Use comprehensive_legal_crawler.py instead.")
    parser.add_argument("--build-index", action="store_true", help="[DEPRECATED] Vector indexing is automatic.")
    
    # MCP options
    parser.add_argument("--mcp-crawl-single", action="store_true", help="Use MCP server to crawl single page.")
    parser.add_argument("--mcp-crawl-smart", action="store_true", help="Use MCP server to smart crawl the forms site.")
    parser.add_argument("--mcp-sources", action="store_true", help="Get available sources from MCP server.")
    parser.add_argument("--mcp-ask", type=str, help="Ask a question using MCP server RAG.")
    parser.add_argument("--mcp-code", type=str, help="Search for code examples using MCP server.")
    
    args = parser.parse_args()

    agent = CourtFormsAgent()
    
    # Vector database operations
    if args.ask:
        print(f"🤖 Asking: {args.ask}")
        answer = agent.answer_question(args.ask, top_k=args.limit)
        print(f"\n📋 Answer:\n{answer}")
    
    if args.search:
        print(f"🔍 Searching for: {args.search}")
        results = agent.search_vector_database(args.search, limit=args.limit)
        if results:
            print(f"\n📋 Found {len(results)} relevant forms:")
            for i, form in enumerate(results, 1):
                print(f"\n{i}. {form['form_code']} - {form['title']}")
                print(f"   Topic: {form['topic']}")
                print(f"   Similarity: {form['similarity']:.3f}")
                if form['url']:
                    print(f"   URL: {form['url']}")
        else:
            print("❌ No forms found matching your search.")
    
    if args.topic:
        print(f"🏷️  Searching topic: {args.topic}")
        results = agent.search_by_topic(args.topic, limit=args.limit)
        if results:
            print(f"\n📋 Found {len(results)} forms in topic '{args.topic}':")
            for i, form in enumerate(results, 1):
                print(f"\n{i}. {form['form_code']} - {form['title']}")
                if form['url']:
                    print(f"   URL: {form['url']}")
        else:
            print(f"❌ No forms found for topic '{args.topic}'.")
    
    if args.topics:
        print("🏷️  Available topics:")
        topics = agent.get_available_topics()
        if topics:
            for i, topic in enumerate(topics, 1):
                print(f"{i:2d}. {topic}")
        else:
            print("❌ No topics found in database.")
    
    if args.stats:
        print("📊 Database Statistics:")
        stats = agent.get_database_stats()
        if "error" not in stats:
            print(f"   Total forms: {stats['total_forms']}")
            print(f"   Total topics: {stats['total_topics']}")
            print(f"   Database ready: {'✅' if stats['database_ready'] else '❌'}")
        else:
            print(f"   ❌ Error: {stats['error']}")
    
    # Legacy operations (show deprecation warnings)
    if args.crawl:
        agent.crawl_forms()
    if args.build_index:
        agent.build_index()
    
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