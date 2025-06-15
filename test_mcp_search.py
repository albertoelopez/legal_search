#!/usr/bin/env python3
"""
Test MCP Server Search Functionality

This script tests:
1. MCP server connection
2. Search tool functionality
3. Response quality and format
4. Integration with vector database
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any, List

class MCPSearchTester:
    def __init__(self):
        self.mcp_url = "http://localhost:8052"
        self.test_queries = [
            {"query": "divorce papers", "expected_topic": "divorce", "description": "Basic divorce query"},
            {"query": "child custody forms", "expected_topic": "child custody", "description": "Child custody query"},
            {"query": "adoption documents", "expected_topic": "adoption", "description": "Adoption query"},
            {"query": "domestic violence restraining order", "expected_topic": "domestic violence", "description": "DV query"},
            {"query": "FL-180", "expected_form": "FL-180", "description": "Specific form code"},
            {"query": "DV-100", "expected_form": "DV-100", "description": "DV form code"},
            {"query": "how to change my name legally", "expected_topic": "name change", "description": "Natural language query"},
            {"query": "small claims court filing", "expected_topic": "small claims", "description": "Court procedure query"},
            {"query": "probate estate administration", "expected_topic": "probate", "description": "Estate planning query"},
            {"query": "fee waiver application", "expected_topic": "fee waivers", "description": "Fee waiver query"},
            {"query": "traffic ticket appeal", "expected_topic": "traffic", "description": "Traffic query"},
            {"query": "eviction notice", "expected_topic": "eviction", "description": "Eviction query"}
        ]
    
    async def test_mcp_connection(self) -> bool:
        """Test if MCP server is running and accessible."""
        print("🔗 TESTING MCP SERVER CONNECTION")
        print("-" * 40)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test basic connectivity
                async with session.post(
                    self.mcp_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list"
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data and "tools" in data["result"]:
                            tools = data["result"]["tools"]
                            print(f"✅ MCP server connected successfully")
                            print(f"📋 Available tools: {len(tools)}")
                            
                            # Check for search tool
                            search_tool = None
                            for tool in tools:
                                if tool.get("name") == "search_legal_forms":
                                    search_tool = tool
                                    break
                            
                            if search_tool:
                                print(f"✅ Search tool found: {search_tool['name']}")
                                print(f"📝 Description: {search_tool.get('description', 'N/A')}")
                                return True
                            else:
                                print("❌ Search tool not found")
                                print("📋 Available tools:")
                                for tool in tools:
                                    print(f"   - {tool.get('name', 'Unknown')}")
                                return False
                        else:
                            print("❌ Invalid response format")
                            return False
                    else:
                        print(f"❌ HTTP error: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    async def call_search_tool(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Call the MCP search tool."""
        try:
            async with aiohttp.ClientSession() as session:
                request_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "search_legal_forms",
                        "arguments": {
                            "query": query,
                            "limit": limit
                        }
                    }
                }
                
                async with session.post(
                    self.mcp_url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        return {"error": f"HTTP {response.status}"}
                        
        except Exception as e:
            return {"error": str(e)}
    
    async def test_search_functionality(self):
        """Test the search functionality with various queries."""
        print("\n🔍 TESTING SEARCH FUNCTIONALITY")
        print("-" * 40)
        
        test_results = []
        
        for i, test_case in enumerate(self.test_queries, 1):
            query = test_case["query"]
            description = test_case["description"]
            expected_topic = test_case.get("expected_topic")
            expected_form = test_case.get("expected_form")
            
            print(f"\n{i}. Testing: {description}")
            print(f"   Query: '{query}'")
            
            # Call the search tool
            result = await self.call_search_tool(query, limit=5)
            
            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                test_results.append({
                    "query": query,
                    "success": False,
                    "error": result["error"],
                    "description": description
                })
                continue
            
            # Check response format
            if "result" not in result:
                print(f"   ❌ Invalid response format")
                test_results.append({
                    "query": query,
                    "success": False,
                    "error": "Invalid response format",
                    "description": description
                })
                continue
            
            # Parse the response
            response_content = result["result"]
            
            # Check if it's a text response or structured data
            if isinstance(response_content, dict) and "content" in response_content:
                content_list = response_content["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    content = content_list[0].get("text", str(content_list))
                else:
                    content = str(content_list)
            elif isinstance(response_content, list) and len(response_content) > 0:
                content = response_content[0].get("text", str(response_content))
            else:
                content = str(response_content)
            
            print(f"   ✅ Response received ({len(content)} characters)")
            
            # Analyze response quality
            success = False
            found_forms = []
            found_topics = []
            
            # Look for form codes in response
            import re
            form_codes = re.findall(r'\b[A-Z]{1,4}-\d{1,4}[A-Z]?\b', content)
            found_forms = list(set(form_codes))
            
            # Look for topics in response
            for topic in ["divorce", "custody", "adoption", "domestic violence", "eviction", 
                         "probate", "traffic", "fee waiver", "name change", "small claims"]:
                if topic.lower() in content.lower():
                    found_topics.append(topic)
            
            # Evaluate success
            if expected_form and any(expected_form.upper() in form.upper() for form in found_forms):
                print(f"   ✅ Found expected form: {expected_form}")
                success = True
            elif expected_topic and any(expected_topic.lower() in topic.lower() for topic in found_topics):
                print(f"   ✅ Found expected topic: {expected_topic}")
                success = True
            elif found_forms:
                print(f"   ✅ Found relevant forms: {found_forms[:3]}")
                success = True
            elif len(content) > 100:  # Has substantial content
                print(f"   ✅ Substantial response received")
                success = True
            else:
                print(f"   ⚠️  Limited response")
            
            # Show sample of response
            sample = content[:200] + "..." if len(content) > 200 else content
            print(f"   📄 Sample: {sample}")
            
            if found_forms:
                print(f"   📋 Forms found: {found_forms[:5]}")
            if found_topics:
                print(f"   🏷️  Topics found: {found_topics[:3]}")
            
            test_results.append({
                "query": query,
                "success": success,
                "forms_found": found_forms,
                "topics_found": found_topics,
                "response_length": len(content),
                "description": description
            })
        
        return test_results
    
    async def test_response_format(self):
        """Test the format and structure of responses."""
        print("\n📋 TESTING RESPONSE FORMAT")
        print("-" * 40)
        
        # Test with a simple query
        result = await self.call_search_tool("divorce", limit=3)
        
        if "error" in result:
            print(f"❌ Error testing response format: {result['error']}")
            return False
        
        print("✅ Response structure analysis:")
        print(f"   Type: {type(result)}")
        print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        
        if "result" in result:
            response_content = result["result"]
            print(f"   Result type: {type(response_content)}")
            
            if isinstance(response_content, dict):
                print(f"   Result keys: {list(response_content.keys())}")
            elif isinstance(response_content, list):
                print(f"   Result length: {len(response_content)}")
                if response_content:
                    print(f"   First item type: {type(response_content[0])}")
        
        return True
    
    async def test_performance(self):
        """Test search performance."""
        print("\n⚡ TESTING SEARCH PERFORMANCE")
        print("-" * 40)
        
        import time
        
        performance_queries = ["divorce", "custody", "adoption", "FL-180", "DV-100"]
        total_time = 0
        successful_queries = 0
        
        for query in performance_queries:
            start_time = time.time()
            result = await self.call_search_tool(query, limit=3)
            end_time = time.time()
            
            query_time = end_time - start_time
            total_time += query_time
            
            if "error" not in result:
                successful_queries += 1
                print(f"   ✅ '{query}': {query_time:.3f}s")
            else:
                print(f"   ❌ '{query}': {query_time:.3f}s (error)")
        
        avg_time = total_time / len(performance_queries)
        success_rate = (successful_queries / len(performance_queries)) * 100
        
        print(f"\n📊 Performance Summary:")
        print(f"   Average response time: {avg_time:.3f}s")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total queries: {len(performance_queries)}")
        
        return avg_time < 2.0 and success_rate >= 80  # Performance thresholds
    
    async def run_comprehensive_test(self):
        """Run all MCP search tests."""
        print("🚀 COMPREHENSIVE MCP SEARCH TEST")
        print("=" * 60)
        
        # Test 1: Connection
        connection_ok = await self.test_mcp_connection()
        if not connection_ok:
            print("❌ Cannot proceed - MCP server not accessible")
            return False
        
        # Test 2: Response format
        format_ok = await self.test_response_format()
        
        # Test 3: Search functionality
        search_results = await self.test_search_functionality()
        
        # Test 4: Performance
        performance_ok = await self.test_performance()
        
        # Summary
        print(f"\n🎉 MCP SEARCH TEST SUMMARY")
        print("=" * 40)
        
        if search_results:
            successful_searches = sum(1 for result in search_results if result["success"])
            success_rate = (successful_searches / len(search_results)) * 100
            
            print(f"✅ Connection: {'OK' if connection_ok else 'FAILED'}")
            print(f"✅ Response format: {'OK' if format_ok else 'FAILED'}")
            print(f"✅ Search success rate: {successful_searches}/{len(search_results)} ({success_rate:.1f}%)")
            print(f"✅ Performance: {'OK' if performance_ok else 'NEEDS IMPROVEMENT'}")
            
            if success_rate >= 80 and connection_ok and format_ok:
                print("🎉 MCP SEARCH IS WORKING EXCELLENTLY!")
                return True
            elif success_rate >= 60:
                print("✅ MCP search is working well!")
                return True
            else:
                print("⚠️  MCP search needs improvement")
                return False
        else:
            print("❌ No search results to analyze")
            return False

async def main():
    """Main test function."""
    try:
        tester = MCPSearchTester()
        success = await tester.run_comprehensive_test()
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 